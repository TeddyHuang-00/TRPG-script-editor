import json
from collections import namedtuple
from dataclasses import dataclass

import streamlit as st
from streamlit_ace import KEYBINDINGS as ace_keybindings
from streamlit_ace import THEMES as ace_themes
from streamlit_ace import st_ace as ace
from plotly import graph_objects as go

st.set_page_config(page_title="TRPG 剧本编辑器", page_icon="📝", layout="wide")

st.title("📝 TRPG 剧本编辑器")

if "content" not in st.session_state:
    st.session_state["content"] = json.dumps(
        {
            "故事起点": {
                "选项 A": "结局 A",
                "选项 B": "结局 B",
                "选项 C": {
                    "故事新分支": {
                        "选项 E": "结局 C",
                        "选项 F": "结局 A",
                    }
                },
                "选项 D": {
                    "故事新分支": {
                        "选项 G": "结局 A",
                        "选项 H": "结局 D",
                    }
                },
            }
        },
        indent=4,
        ensure_ascii=False,
    )


@dataclass
class Node:
    name: str
    children: dict
    id: str


@dataclass
class Link:
    event: str
    option: str
    children: str


def check_json_health(json_data: str):
    try:
        json.loads(json_data)
        return True
    except json.JSONDecodeError:
        return False


def parse_story():
    story_data = json.loads(st.session_state["content"])
    if not story_data or not isinstance(story_data, dict):
        return None, None, None
    nodes = [
        Node(event, outcomes, chr(ord("A") + idx))
        for idx, (event, outcomes) in enumerate(story_data.items())
    ]
    events: list[str] = []
    labels: list[list[str]] = []
    links: list[Link] = []
    while nodes:
        node = nodes.pop()
        branch_idx = 0
        if node.name not in events:
            events.append(node.name)
            labels.append([node.id])
        else:
            labels[events.index(node.name)].append(node.id)
        for option, outcome in node.children.items():
            if isinstance(outcome, dict):
                links.extend(Link(node.name, option, name) for name in outcome.keys())
                nodes.extend(
                    Node(event, outcomes, node.id + f"-{idx+branch_idx}")
                    for idx, (event, outcomes) in enumerate(outcome.items())
                )
                branch_idx += len(outcome)
            else:
                links.append(Link(node.name, option, outcome))
                if outcome not in events:
                    events.append(outcome)
                    labels.append([node.id + "-end"])
                else:
                    labels[events.index(outcome)].append(node.id + "-end")
    return events, labels, links


with st.sidebar:
    # Editor settings
    st.subheader("编辑器设置")
    st.selectbox("主题", options=ace_themes, index=22, key="theme")
    st.selectbox("键盘绑定", options=ace_keybindings, index=3, key="key_binding")
    st.slider("字体大小", min_value=4, max_value=48, value=16, key="font_size")
    st.checkbox("自动换行", value=True, key="wrap")
    st.checkbox("显示行号", value=True, key="show_line_numbers")

L, R = st.columns(2)

with L:
    # Editor
    ace(
        value=st.session_state["content"],
        placeholder="在这里输入剧本",
        language="json",
        theme=st.session_state["theme"],
        keybinding=st.session_state["key_binding"],
        font_size=st.session_state["font_size"],
        tab_size=4,
        wrap=st.session_state["wrap"],
        show_gutter=st.session_state["show_line_numbers"],
        min_lines=24,
        key="content",
    )

    # Help message
    with st.expander("编辑器使用"):
        st.markdown(
            """
            请在左侧编辑器中编辑剧本内容
            - 使用 `Tab` 键缩进
            - 使用 `Enter` 键换行
            - 并列项之间用逗号分隔，最后一个选项后不要加逗号
            - **所有字符串需要加上双引号！！！**
            """
        )
    with st.expander("剧情基本单元"):
        st.write(
            """
            剧本的基本单元为 `{事件: {选项: 事件}}` 结构，均使用 `字典` 表示（`{}`），比如以下展示一个最基础的剧情：
            """
        )
        st.write(
            f"""
            ```
            {json.dumps(
                {
                    "小明准备去上课时发现自己忘记写作业了": {
                        "开摆": "挂科啦",
                        "和老师解释": "补交作业",
                        "装病": "被要求开医院证明",
                    },
                },
                indent=4,
                ensure_ascii=False,
            )}
            """
        )
    with st.expander("分支剧情嵌套"):
        st.write(
            """
            如果一个选项会导致进入一个新的事件分支，那么可将上述基本单元进行嵌套，形如 `{事件: {选项: {事件: {选项: 事件}}}}`，比如以下展示一个简单的分支剧情：
            """
        )
        st.write(
            f"""
            ```
            {
                json.dumps(
                    {
                        "起点": {
                            "选项 A": {
                                "分支 A": {
                                    "选项 C": "结束",
                                    "选项 D": "结束",
                                }
                            },
                            "选项 B": {
                                "分支 B": {
                                    "选项 E": "结束",
                                    "选项 F": "结束",
                                }
                            },
                        }
                    },
                    indent=4,
                    ensure_ascii=False,
                )
            }
            """
        )

with R:
    # Preview
    # st.subheader("预览")

    if not check_json_health(st.session_state["content"]):
        # Failed to parse JSON
        st.error("格式错误，请对照下方说明和编辑器提示修正")
        st.stop()

    # with st.expander("原始数据"):
    #     st.json(json.loads(st.session_state["content"]))

    events, labels, links = parse_story()
    if not events or not labels or not links:
        # Failed to parse story
        st.error("格式错误，请对照下方说明和编辑器提示修正")
        st.stop()
    sources = [events.index(l.event) for l in links]
    targets = [events.index(l.children) for l in links]
    options = [l.option for l in links]
    values = [1] * len(targets)
    slugs = [",".join(sorted(l)) for l in labels]
    # st.write(events)
    # st.write(labels)
    # st.write(links)
    fig = go.Figure(
        data=[
            go.Sankey(
                node=dict(
                    label=slugs,
                    customdata=events,
                    hovertemplate="%{customdata}<extra></extra>",
                ),
                link=dict(
                    source=sources,
                    target=targets,
                    value=values,
                    customdata=options,
                    hovertemplate="%{customdata}<extra></extra>",
                ),
            )
        ]
    )
    fig.update_layout(title_text="剧本预览", font_size=16)
    st.plotly_chart(fig)

    # Upload
    with st.form(key="载入", clear_on_submit=True):
        file = st.file_uploader("上传 JSON 文件", type="json")
        if st.form_submit_button("载入"):
            if file:
                content = file.read().decode("utf-8")
                if check_json_health(content):
                    st.session_state["content"] = json.dumps(
                        json.loads(content), indent=4, ensure_ascii=False
                    )
                    st.success("载入成功")
                else:
                    st.error("JSON 格式错误")
            else:
                st.warning("请选择文件")
    # Download
    st.download_button(
        label="导出为 JSON",
        data=json.dumps(
            json.loads(st.session_state["content"]), indent=4, ensure_ascii=False
        ),
        file_name="剧本.json",
        mime="application/json",
    )
