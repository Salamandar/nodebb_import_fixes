#!/usr/bin/env python3

import re
from typing import Tuple, List, Dict, Any
import requests
import logging
import yaml
import json


class ForumClient():
    def __init__(self, url: str, auth_token: str) -> None:
        self.url = url
        self.token = auth_token
        # self.test_auth()

    def test_auth(self) -> None:
        requests.get(f"{self.url}/api/notifications", timeout=2).raise_for_status()

    def get_categories(self) -> Dict[int, str]:
        response = requests.get(f"{self.url}/api/categories", timeout=2).json()

        def recurse_categories(category: Dict[str, Any]) -> Dict[int, str]:
            rec_cat: Dict[int, str] = {}
            rec_cat[int(category["cid"])] = category["slug"]
            for child in category["children"]:
                rec_cat.update(recurse_categories(child))
            return rec_cat

        categories: Dict[int, str] = {}
        for category in response["categories"]:
            categories.update(recurse_categories(category))

        return categories

    def get_topics_of_category(self, category_id: int) -> Dict[int, str]:
        logging.info(f"Downloading info of category {category_id}...")
        # First get some info about the category
        category_data = requests.get(f"{self.url}/api/category/{category_id}", timeout=2).json()
        name = category_data["name"]
        slug = category_data["slug"]
        topics_count = category_data["topic_count"]
        posts_count = category_data["post_count"]
        logging.debug(f"{topics_count} topics and {posts_count} posts in category {name}.")

        # Now get topics
        all_topics: Dict[int, str] = {}
        next_topic = 1
        while next_topic <= topics_count:
            topics = requests.get(f"{self.url}/api/category/{slug}/{next_topic}", timeout=5).json()["topics"]
            next_topic += len(topics)

            all_topics.update({topic["tid"]: topic["title"] for topic in topics})

            percent = int(100 * len(all_topics.keys()) / topics_count)
            print(f"{percent}%..", end="", flush=True)

        print("")
        return all_topics

    def get_topic_content(self, topic_id: int) -> Dict[int, str]:
        logging.info(f"Downloading info of topic {topic_id}...")
        # First get some info about the topic
        topic_data = requests.get(f"{self.url}/api/topic/{topic_id}", timeout=2).json()
        slug = topic_data["slug"]
        posts_count = topic_data["postcount"]

        # Now get posts
        all_posts: Dict[int, str] = {}
        next_post = 1
        while next_post <= posts_count:
            posts = requests.get(f"{self.url}/api/topic/{slug}/{next_post}", timeout=5).json()["posts"]
            next_post += len(posts)

            all_posts.update({post["pid"]: post["content"] for post in posts})

            percent = int(100 * len(all_posts.keys()) / posts_count)
            print(f"{percent}%..", end="", flush=True)

        print("")
        return all_posts

    def get_post_content(self, post_id: int) -> Dict[int, str]:
        new_path = requests.get(f"{self.url}/api/post/{post_id}", timeout=2).json()
        url = f"{self.url}/api{new_path}"
        posts = requests.get(url).json()["posts"]
        return {post["pid"]: post["content"] for post in posts}

    def set_post_content(self, topic_id: int, post_id: int, content: str) -> None:
        url = f"{self.url}/api/v1/posts/{post_id}"
        result = requests.put(
            url,
            headers={"Authorization": f"Bearer {self.token}"},
            data={
                # "pid": post_id,
                "content": content
            },
            timeout=3
        )

class Reparations:
    @staticmethod
    def image_uploads(text: str) -> str:
        # Get all the uploads and their urls...
        uploads_rex = \
            r"<a download=\"([^\"]*)\" class=\"imported-anchor-tag\" href=\"([^\"]*)\" .*</a>"
        uploads = dict(re.findall(uploads_rex, text))

        # Replace the attachments with the markdown equivalence...
        def replace(matchobj):
            # Two line breaks because of <p>
            image_markdown_pattern = "\n\n![{name}]({url})"
            image_name = matchobj.group(1)
            try:
                upload_url = uploads[image_name]
            except KeyError as err:
                logging.error(f"Missing attachment {err}.")
                upload_url = ""
            finally:
                return image_markdown_pattern.format(url=upload_url, name=image_name)

        attachments_rex = r"<ATTACHMENT filename=\"([^\"]*)\".*</ATTACHMENT>"
        text = re.sub(attachments_rex, replace, text)

        # Finally remove the uploads
        text = re.sub(uploads_rex, "", text)

        return text

    @staticmethod
    def image_html(text: str) -> str:
        image_html_rex = r"<p><img src=\"([^\"]*)\" alt=\"([^\"]*)\" " \
            r"class=\"img-responsive img-markdown\" /><br\s?/>"
        # Two line breaks because of <p>
        image_markdown = "\n\n![{name}]({url})"

        def replace(matchobj) -> str:
            url, name = matchobj.group(1), matchobj.group(2)
            return image_markdown.format(url=url, name=name)

        return re.sub(image_html_rex, replace, text)

    @staticmethod
    def multiple_br(text: str) -> str:
        text = re.sub(r"<br\s?/>(\s?<br\s?/>)+", "<br/>", text)
        text = re.sub(r"</p></p>", "</p>", text)
        return text

    @staticmethod
    def link_text(text: str) -> str:
        # TODO:
        link_html_rex = r"<URL url=\".*\">.*LINK_TEXT text=&quot;<a href=\".*\".*href=\"([^\"]*)\".*</URL>(&quot; onclick=&quot;window.open\(this.href\);return false;)?"
        link_markdown = "\n[{url}]({url})\n"

        def replace(matchobj) -> str:
            url = matchobj.group(1)
            return link_markdown.format(url=url)

        return re.sub(link_html_rex, replace, text)

    @staticmethod
    def quote(text: str) -> str:
        quote_bbcode_rex = r"\[quote=&quot;([^&]*)&quot;\]([^\[]*)\[/quote\]"
        # Two line breaks because of <p>
        quote_markdown = "\n@{name} a dit :\n\n> {content}\n\n"

        def replace(matchobj) -> str:
            name, content = matchobj.group(1), matchobj.group(2)
            content = content.replace("<br/>\n", "\n> ")
            return quote_markdown.format(name=name, content=content)

        return re.sub(quote_bbcode_rex, replace, text)


def main():
    logging.getLogger().setLevel(logging.INFO)

    try:
        with open("config.yaml", encoding="utf-8") as config_yaml:
            config = yaml.load(config_yaml, Loader=yaml.SafeLoader)
    except Exception as err:
        logging.fatal(f"Could not read configuration file: {err}")
        exit(1)

    try:
        forum = ForumClient(config["server"]["url"], config["server"]["token"])
    except requests.exceptions.HTTPError as err:
        logging.fatal(f"{err}")
        exit(1)

    def handle_post(topic_id: int, post_id: int, orig_text: str) -> None:
        post_msg = f"topic {topic_id}, post {post_id}"
        text = orig_text
        try:
            reparation_config = config["reparation"]
            for reparation in reparation_config.keys():
                if reparation_config[reparation]:
                    text = getattr(Reparations, reparation)(text)
        except Exception as err:
            logging.error(f"Could not handle post text for {post_msg}: {err}")
            return

        if text == orig_text:
            logging.info(f"Not updated: {post_msg}")
            return

        if config["debug"]:
            print(orig_text)
            print("----------")
            print(text)
            return

        try:
            forum.set_post_content(topic_id, post_id, text)
        except Exception as err:
            logging.error(f"Could not update post {post_msg}: {err}")
            return

        logging.info(f"Updated: {post_msg}")

    # for topic_id in config["selection"]["topic_include"]:
    #     post_id = 75028
    #     posts = forum.get_post_content(post_id)
    #     handle_post(topic_id, post_id, posts[post_id])

        # posts = forum.get_topic_content(topic_id)
        # for pid, text in posts.items():
        #     handle_post(topic_id, pid, text)

    categories = forum.get_categories()
    for cid, slug in categories.items():
        forum.get_topics_of_category(cid)


if __name__ == "__main__":
    main()
