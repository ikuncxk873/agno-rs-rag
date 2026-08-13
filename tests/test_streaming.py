from types import SimpleNamespace

from app.streaming import extract_sources


def make_output(*messages):
    built = []
    for role, tool_name, content in messages:
        built.append(SimpleNamespace(role=role, tool_name=tool_name, content=content))
    return SimpleNamespace(messages=built)


def make_tool_output(content):
    return make_output(("tool", "search_knowledge_base", content))


def test_extract_sources_list_json():
    output = make_tool_output('[{"name": "文档A.txt"}, {"name": "文档B.txt"}, {"name": "文档A.txt"}]')
    assert extract_sources(output) == ["文档A.txt", "文档B.txt"]


def test_extract_sources_dict_json():
    output = make_tool_output('{"name": "单文档.txt"}')
    assert extract_sources(output) == ["单文档.txt"]


def test_extract_sources_invalid_json():
    output = make_tool_output("不是 JSON")
    assert extract_sources(output) == []


def test_extract_sources_none_content():
    output = make_tool_output(None)
    assert extract_sources(output) == []


def test_extract_sources_ignores_other_roles_and_tools():
    output = make_output(
        ("user", None, "提问"),
        ("tool", "other_tool", '[{"name": "无关.txt"}]'),
        ("tool", "search_knowledge_base", '[{"name": "相关.txt"}]'),
    )
    assert extract_sources(output) == ["相关.txt"]


def test_extract_sources_no_messages():
    assert extract_sources(SimpleNamespace()) == []
    assert extract_sources(SimpleNamespace(messages=[])) == []


def test_extract_sources_doc_without_name():
    output = make_tool_output('[{"content": "没有 name 字段"}, {"name": "有名字.txt"}]')
    assert extract_sources(output) == ["有名字.txt"]
