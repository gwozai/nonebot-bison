import typing
from datetime import datetime
import xml.etree.ElementTree as ET

import pytz
import respx
import pytest
from nonebug.app import App
from httpx import Response, AsyncClient

from .utils import get_file

if typing.TYPE_CHECKING:
    pass


@pytest.fixture()
def dummy_user(app: App):
    from nonebot_bison.types import User

    user = User(123, "group")
    return user


@pytest.fixture()
def user_info_factory(app: App, dummy_user):
    from nonebot_bison.types import UserSubInfo

    def _user_info(category_getter, tag_getter):
        return UserSubInfo(dummy_user, category_getter, tag_getter)

    return _user_info


@pytest.fixture()
def rss(app: App):
    from nonebot_bison.utils import ProcessContext
    from nonebot_bison.platform import platform_manager

    return platform_manager["rss"](ProcessContext(), AsyncClient())


@pytest.fixture()
def update_time_feed_1():
    file = get_file("rss-twitter-ArknightsStaff.xml")
    root = ET.fromstring(file)
    item = root.find("channel/item")
    current_time = datetime.now(pytz.timezone("GMT")).strftime("%a, %d %b %Y %H:%M:%S %Z")
    pubdate_elem = item.find("pubDate")
    pubdate_elem.text = current_time
    return ET.tostring(root, encoding="unicode")


@pytest.fixture()
def update_time_feed_2():
    file = get_file("rss-ruanyifeng.xml")
    root = ET.fromstring(file)
    current_time = datetime.now(pytz.timezone("GMT")).strftime("%a, %d %b %Y %H:%M:%S %Z")
    published_element = root.find(".//{*}published")
    published_element.text = current_time
    return ET.tostring(root, encoding="unicode")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_1(
    rss,
    user_info_factory,
    update_time_feed_1,
):
    ## 标题重复的情况
    rss_router = respx.get("https://rsshub.app/twitter/user/ArknightsStaff")
    rss_router.mock(return_value=Response(200, text=get_file("rss-twitter-ArknightsStaff-0.xml")))
    target = "https://rsshub.app/twitter/user/ArknightsStaff"
    res1 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed_1))
    res2 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://twitter.com/ArknightsStaff/status/1659091539023282178"
    assert (
        post1.text
        == "【#統合戦略】 引き続き新テーマ「ミヅキと紺碧の樹」の新要素及びシステムの変更点を一部ご紹介します！"
        " 今回は「灯火」、「ダイス」、「記号認識」、「鍵」についてです。詳細は添付の画像をご確認ください。"
        "#アークナイツ https://t.co/ARmptV0Zvu"
    )


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_2(
    rss,
    user_info_factory,
    update_time_feed_2,
):
    ## 标题与正文不重复的情况
    rss_router = respx.get("https://www.ruanyifeng.com/blog/atom.xml")
    rss_router.mock(return_value=Response(200, text=get_file("rss-ruanyifeng-0.xml")))
    target = "https://www.ruanyifeng.com/blog/atom.xml"
    res1 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed_2))
    res2 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "http://www.ruanyifeng.com/blog/2023/05/weekly-issue-255.html"
    assert (
        post1.text == "科技爱好者周刊（第 255 期）：对待 AI 的正确态度\n\n这里记录每周值得分享的科技内容，周五发布。..."
    )


@pytest.fixture()
def update_time_feed_3():
    file = get_file("rss-github-atom.xml")
    root = ET.fromstring(file)
    current_time = datetime.now(pytz.timezone("GMT")).strftime("%a, %d %b %Y %H:%M:%S %Z")
    published_element = root.findall(".//{*}updated")[1]
    published_element.text = current_time
    return ET.tostring(root, encoding="unicode")


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_3(
    rss,
    user_info_factory,
    update_time_feed_3,
):
    ## 只有<updated>没有<published>
    rss_router = respx.get("https://github.com/R3nzTheCodeGOD/R3nzSkin/releases.atom")
    rss_router.mock(return_value=Response(200, text=get_file("rss-github-atom-0.xml")))
    target = "https://github.com/R3nzTheCodeGOD/R3nzSkin/releases.atom"
    res1 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=update_time_feed_3))
    res2 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://github.com/R3nzTheCodeGOD/R3nzSkin/releases/tag/v3.0.9"
    assert post1.text == "R3nzSkin\n\nNo content."


@pytest.mark.asyncio
@respx.mock
async def test_fetch_new_4(
    rss,
    user_info_factory,
):
    ## 没有日期信息的情况
    rss_router = respx.get("https://rsshub.app/wallhaven/hot?limit=5")
    rss_router.mock(return_value=Response(200, text=get_file("rss-top5-old.xml")))
    target = "https://rsshub.app/wallhaven/hot?limit=5"
    res1 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res1) == 0

    rss_router.mock(return_value=Response(200, text=get_file("rss-top5-new.xml")))
    res2 = await rss.fetch_new_post(target, [user_info_factory([], [])])
    assert len(res2[0][1]) == 1
    post1 = res2[0][1][0]
    assert post1.url == "https://wallhaven.cc/w/85rjej"
    assert post1.text == "85rjej.jpg"
