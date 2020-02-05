# coding=utf-8
import codecs
import json
import os
import time

import feedparser
import requests
from git import Repo

rss_urls = [
    'http://www.freebuf.com/feed', 'http://paper.seebug.org/rss/',
    'https://evi1cg.me/feed', 'http://www.91ri.org/feed',
    'https://xz.aliyun.com/feed'
]
tuling_key = ""
short_url_token = ""
repo_path = os.path.dirname(os.path.realpath(__file__))


def parse_config(config_path):
    """ 解析配置文件 """
    json_dict = json.load(open(config_path))
    global tuling_key
    global short_url_token
    tuling_key, short_url_token = json_dict["tuling_key"], json_dict[
        "short_url_token"]


def add_personal_kb(question, answer):
    """ 新增图灵机器人语料库. """
    kblist = [{"question": question, "answer": answer}]
    payload = {}
    payload["apikey"] = tuling_key
    payload["timestamp"] = time.time()
    payload["data"] = {}
    payload["data"]["list"] = kblist
    r = requests.post('http://www.tuling123.com/v1/kb/import', json=payload)


def update_personal_kb(question, answer):
    """ 更新图灵机器人语料库. """
    kblist = [{"question": question, "answer": answer, "id": "1110195"}]
    payload = {}
    payload["apikey"] = tuling_key
    payload["timestamp"] = time.time()
    payload["data"] = {}
    payload["data"]["list"] = kblist
    r = requests.post('http://www.tuling123.com/v1/kb/update', json=payload)


def delete_personal_kb():
    """ 删除图灵机器人语料库指定答案. """
    payload = {}
    payload["apikey"] = tuling_key
    payload["timestamp"] = time.time()
    payload["data"] = {"clear": False, "ids": [1110199]}
    r = requests.post('http://www.tuling123.com/v1/kb/delete', json=payload)


def select_personal_kb(question):
    """ 查询图灵机器人语料库. """
    payload = {}
    payload["apikey"] = tuling_key
    payload["timestamp"] = time.time()
    payload["data"] = {
        "pages": {
            "pageNumber": 1,
            "pageSize": 10,
            "searchBy": question
        }
    }
    r = requests.post('http://www.tuling123.com/v1/kb/select', json=payload)


def get_feeds_lastday_published(rss_url):
    """ 获取订阅内容. """
    lastday_published_news = []
    timestamp = time.time() - 86400
    time_tuple = time.localtime(timestamp)
    time_str = time.strftime("%Y-%m-%d", time_tuple)
    feeds = feedparser.parse(rss_url)
    for entry in feeds['entries']:
        if entry.published_parsed is not None:
            entry_time_str = time.strftime("%Y-%m-%d", entry.published_parsed)
            if entry_time_str == time_str:
                item = {
                    'link': entry.link,
                    'title': entry.title,
                }
                lastday_published_news.append(item)
    return lastday_published_news


def fetch_all_feeds():
    """ 遍历rss_url,获取所有订阅. """
    lastday_news = []
    for url in rss_urls:
        single_news = get_feeds_lastday_published(url)
        lastday_news.extend(single_news)
    return lastday_news


def write_markdown_file(news):
    """ 把订阅消息写入markdown格式的文件中. """
    if not news:
        print("No feed news in last day.")
    else:
        timestamp = time.time()
        time_tuple = time.localtime(timestamp)
        current_year = time.strftime("%Y")
        file_name = time.strftime("%m-%d-daily.md", time_tuple)
        docs_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "docs", current_year)
        if os.path.exists(docs_path):
            md_file = codecs.open(
                os.path.join(docs_path, file_name), 'w', 'utf-8')
            md_file.write(u"# Quick news\n\n")
            for feed_new in news:
                md_file.write("## %s\n\n%s\n\n" % (feed_new['title'],
                                                   feed_new['link']))

            md_file.flush()
            md_file.close()
        else:
            os.mkdir(docs_path)


def convert_feed_to_buffer(news):
    """ 转化为buffer. """
    result = ""
    limit = 512
    if not news:
        return "No feed news in last day."
    else:
        result = result + "Quick news\n"
        index = 1
        for feed_new in news:
            cur_len = len(result)
            append_str = "%d. %s\n%s\n" % (
                index, feed_new['title'],
                convert_to_short_link(feed_new['link']))
            if cur_len + len(append_str) <= limit:
                result = result + append_str
            else:
                break
            index = index + 1
    return result


def convert_to_short_link(org_link):
    """ 转化为短连接. """
    payload = {"Url": org_link}
    headers = {"Token": short_url_token}
    short_link = org_link
    print(payload)
    max_try = 3
    while short_link == org_link and max_try > 0:
        max_try = max_try - 1
        r = requests.post(
            'https://dwz.cn/admin/v2/create', json=payload, headers=headers)
        print(r.text)
        if (r.status_code == 200):
            result = r.json()
            if result["Code"] == 0:
                short_link = result["ShortUrl"]
    return short_link


def git_daily_news():
    """ 提交md文件到远程仓库. """
    timestamp = time.time()
    time_tuple = time.localtime(timestamp)
    current_year = time.strftime("%Y")
    file_name = time.strftime("%m-%d-daily.md", time_tuple)
    commit_tag = time.strftime("%Y-%m-%d-daily-news", time_tuple)
    repo = Repo(repo_path)
    index = repo.index
    push_file_name = os.path.join("docs", current_year, file_name)
    print(push_file_name)
    index.add([push_file_name])
    index.commit(commit_tag)
    remote = repo.remote()
    remote.push()


if __name__ == '__main__':
    parse_config("/home/pi/cynews.json")
    news = fetch_all_feeds()
    write_markdown_file(news)
    update_personal_kb("每日播报", convert_feed_to_buffer(news))
    git_daily_news()
