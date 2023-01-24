#!/usr/bin/env python3

import re
from typing import Tuple, List
import requests
import yaml


class ForumClient():
    def __init__(self, url: str, auth_token: str) -> None:
        self.url = url
        self.token = auth_token

    def get_topic_content(self, topic_id: int) -> List[Tuple[int, str]]:
        topic_data = requests.get(f"{self.url}/api/topic/{topic_id}", timeout=2).json()
        return [
            (post["pid"], post["content"])
            for post in topic_data["posts"]
        ]
        # post_data = topic_data["posts"][post_id]
        # return post_data["pid"], post_data["content"]

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
        print(result.url, result.text)

    def repair_text_image_uploads(self, text: str) -> str:
        # Get all the uploads and their urls...
        uploads_rex = \
            r"<a download=\"([^\"]*)\" class=\"imported-anchor-tag\" href=\"([^\"]*)\" .*</a>"
        uploads = dict(re.findall(uploads_rex, text))

        # Replace the attachments with the markdown equivalence...
        def replace(matchobj):
            # Two line breaks because of <p>
            image_markdown_pattern = "\n\n![{name}]({url})"
            image_name = matchobj.group(1)
            upload_url = uploads[image_name]
            return image_markdown_pattern.format(url=upload_url, name=image_name)

        attachments_rex = r"<ATTACHMENT filename=\"([^\"]*)\".*</ATTACHMENT>"
        text = re.sub(attachments_rex, replace, text)

        # Finally remove the uploads
        text = re.sub(uploads_rex, "", text)

        return text

    def repair_text_multiple_br(self, text: str) -> str:
        text = re.sub(r"<br\s?/>\s?<br\s?/>", "<br/>", text)
        text = re.sub(r"</p></p>", "</p>", text)
        return text

    def repair_text_image_html_to_markdown(self, text: str) -> str:
        image_html_rex = r"<p><img src=\"([^\"]*)\" alt=\"([^\"]*)\" " \
            r"class=\"img-responsive img-markdown\" /><br\s?/>"
        # Two line breaks because of <p>
        image_markdown = "\n\n![{name}]({url})"

        def replace(matchobj):
            url, name = matchobj.group(1), matchobj.group(2)
            return image_markdown.format(url=url, name=name)

        return re.sub(image_html_rex, replace, text)


def main():
    with open("config.yaml", encoding="utf-8") as config_yaml:
        config = yaml.load(config_yaml, Loader=yaml.SafeLoader)
        url = config["url"]
        token = config["token"]
        topic_id = config["test_topic"]

    forum = ForumClient(url, token)

    posts = forum.get_topic_content(topic_id)

    for pid, text in posts:
        text = forum.repair_text_image_uploads(text)
        text = forum.repair_text_image_html_to_markdown(text)
        text = forum.repair_text_multiple_br(text)

        print(text)
        forum.set_post_content(topic_id, pid, text)


if __name__ == "__main__":
    main()
