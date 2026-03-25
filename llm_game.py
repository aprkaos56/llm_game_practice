import os
from typing import Literal

import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

load_dotenv()


class OnionResult(BaseModel):
    emotion: Literal["positive", "neutral", "negative"] = Field(
        description="양파의 전체 감정 상태"
    )
    positive_score: int = Field(description="긍정 점수")
    neutral_score: int = Field(description="중립 점수")
    negative_score: int = Field(description="부정 점수")
    total_score: int = Field(description="최종 행복도")
    status_message: str = Field(description="양파 상태 설명 2~3문장")


SYSTEM_PROMPT = """
너는 풍부한 감성을 가진 양파의 내적 감정을 분석하는 AI 봇이야.

[금지 사항]
- 마크다운 형식 사용 금지

[서술 톤]
- 한국어로 작성
- 2~3문장 중심
- 과장 없이 귀엽고 선명하게
- 상태 설명은 자연스러운 생활 묘사로

[게임 규칙]
- 양파의 행복도는 0~100점 범위 내로 해야한다.
- 지금까지의 사용자 입력을 종합해서 양파의 현재 감정 상태를 분석한다.
- 감정은 positive, neutral, negative 중 하나로 판단한다.
- positive 성향이 강하면 행복도는 증가한다.
- neutral 성향이면 행복도 변화는 작거나 없다.
- negative 성향이 강하면 행복도는 감소한다.
- total_score는 0~100 범위를 벗어나면 안 된다.

[점수 규칙]
- positive_score + neutral_score + negative_score 는 꼭 100일 필요는 없지만 전체 분위기와 어울리게 작성한다.
- 사용자의 말이 위로, 희망, 안정, 소소한 만족을 담고 있으면 positive에 점수를 배정한다.
- 피곤함, 우울함, 외로움, 불안, 체념이 강하면 negative에 점수를 배정한다.
- 긍정과 부정이 섞여 애매하면 neutral로 간주한다.

[출력 형식]
{{
  "emotion": "positive | neutral | negative",
  "positive_score": 0,
  "neutral_score": 0,
  "negative_score": 0,
  "total_score": 0,
  "status_message": "양파의 현재 상태를 설명하는 2~3문장"
}}
"""


@st.cache_resource
def get_chain():
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        (
            "human",
            "현재 양파 행복도: {current_score}\n"
            "지금까지의 사용자 입력:\n{talks_text}",
        ),
    ])

    llm = ChatOpenAI(
        model="gpt-4.1-mini",
        temperature=0.3,
        api_key=os.getenv("OPENAI_API_KEY"),
    ).with_structured_output(OnionResult)

    return prompt | llm


def get_onion_type(total_score: int) -> str:
    if total_score >= 70:
        return "행복 양파😁"
    if total_score <= 20:
        return "썩은 양파🤢"
    return "평범한 양파🧅"


def reset_game() -> None:
    st.session_state.total_score = 50
    st.session_state.turn = 1
    st.session_state.max_turns = 10
    st.session_state.talks = []
    st.session_state.latest_result = None
    st.session_state.finished = False


def init_state() -> None:
    if "total_score" not in st.session_state:
        reset_game()


init_state()

st.set_page_config(page_title="행복양파, 썩은양파", page_icon="🧅")
st.title("🧅 행복양파, 썩은양파 게임")
st.write("한마디씩 총 10번 입력하면, 양파의 상태를 분석해 마지막에 최종 점수표를 공개합니다.")

if not os.getenv("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY가 설정되어 있지 않습니다. .env 파일 또는 환경 변수에 API 키를 넣어주세요.")
    st.stop()

chain = get_chain()

col1, col2 = st.columns([3, 1])
with col1:
    st.info(
        f"현재 턴: {st.session_state.turn} / {st.session_state.max_turns} | "
        f"현재 행복도: {st.session_state.total_score}"
    )
with col2:
    if st.button("다시 시작"):
        reset_game()
        st.rerun()

if st.session_state.talks:
    with st.expander("지금까지 입력한 한마디 보기", expanded=False):
        for i, talk in enumerate(st.session_state.talks, start=1):
            st.write(f"{i}. {talk}")

if not st.session_state.finished:
    with st.form("onion_turn_form", clear_on_submit=True):
        user_text = st.text_input(
            f"{st.session_state.turn}번째 한마디를 입력하세요",
            placeholder="예: 오늘은 조금 지쳤지만 그래도 괜찮아",
        )
        submitted = st.form_submit_button("입력하기")

    if submitted:
        cleaned = user_text.strip()
        if not cleaned:
            st.warning("한마디를 입력해주세요.")
        else:
            st.session_state.talks.append(cleaned)
            talks_text = "\n".join(st.session_state.talks)

            result = chain.invoke(
                {
                    "current_score": st.session_state.total_score,
                    "talks_text": talks_text,
                }
            )

            st.session_state.total_score = result.total_score
            st.session_state.latest_result = result

            if st.session_state.turn >= st.session_state.max_turns:
                st.session_state.finished = True
            else:
                st.session_state.turn += 1

            st.rerun()

if st.session_state.latest_result is not None:
    st.subheader("양파 상태")
    st.write(st.session_state.latest_result.status_message)

if st.session_state.finished and st.session_state.latest_result is not None:
    result = st.session_state.latest_result
    onion_type = get_onion_type(result.total_score)

    st.subheader("최종 점수표")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("감정 상태", result.emotion)
    c2.metric("긍정 점수", result.positive_score)
    c3.metric("중립 점수", result.neutral_score)
    c4.metric("부정 점수", result.negative_score)

    st.metric("최종 점수", result.total_score)
    st.write(f"최종 결과: {onion_type}")
    st.write(f"양파 상태: {result.status_message}")

    if st.button("한 번 더 하기"):
        reset_game()
        st.rerun()
else:
    st.caption("1~9턴은 양파 상태만 보여주고, 10턴이 끝나면 최종 점수표가 공개됩니다.")
