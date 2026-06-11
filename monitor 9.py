import requests
import time
import re
from datetime import datetime

# ================================================
#  설정 (여기만 수정하면 됩니다)
# ================================================

WEBHOOK_URL = ""

ROOM_NO = 9
SEAT_MAP_URL = f"http://168.131.31.182/CHONNAM_MOBILE/seatMap.do?roomNo={ROOM_NO}&searchGB=S"

# 관심 좌석 번호 목록
TARGET_SEATS = set(list(range(1, 46)) + list(range(105, 112)))

# 조회 주기 (초)
CHECK_INTERVAL = 5

# ================================================
#  내부 상태 (수정 불필요)
# ================================================

# 이전 조회에서 비어 있던 좌석 (처음엔 빈 집합)
prev_empty = set()
# 처음 실행 여부 플래그
first_run = True

# ================================================
#  함수
# ================================================

def get_used_seats():
    """seatMap.do 페이지에서 사용 중인 좌석 번호 집합을 반환합니다."""
    try:
        resp = requests.get(SEAT_MAP_URL, timeout=10)
        resp.raise_for_status()
        # useSeatNo.push("숫자"); 패턴 추출
        nums = re.findall(r'useSeatNo\.push\("(\d+)"\)', resp.text)
        return set(int(n) for n in nums)
    except requests.RequestException as e:
        print(f"[{now()}] ⚠️  요청 실패: {e}")
        return None  # 실패 시 None 반환 → 알림 스킵


def calc_empty(used_seats):
    """관심 좌석 중 비어 있는 좌석 집합을 반환합니다."""
    return TARGET_SEATS - used_seats


def send_discord(empty_seats, new_seats):
    """디스코드 웹훅으로 알림을 보냅니다."""
    count = len(empty_seats)
    new_count = len(new_seats)

    # 좌석 목록을 보기 좋게 정렬
    sorted_empty = sorted(empty_seats)
    sorted_new   = sorted(new_seats)

    message = (
        f"<> 🪑 **백야 24H 4F 좌석 알림**\n"
        f"🕐 {now()}\n\n"
        f"✅ **새로 빈 좌석** ({new_count}개): `{sorted_new}`\n"
        f"📋 **현재 빈 좌석 전체** ({count}개): `{sorted_empty}`"
    )

    payload = {"content": message}
    try:
        r = requests.post(WEBHOOK_URL, json=payload, timeout=10)
        r.raise_for_status()
        print(f"[{now()}] ✅ 디스코드 알림 전송 완료 (새 빈자리: {sorted_new})")
    except requests.RequestException as e:
        print(f"[{now()}] ⚠️  디스코드 전송 실패: {e}")


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ================================================
#  메인 루프
# ================================================

def main():
    global prev_empty, first_run

    print("=" * 50)
    print("  도서관 좌석 모니터링 시작")
    print(f"  대상: 백야 24H 4F (roomNo={ROOM_NO})")
    print(f"  관심 좌석: 1~45, 105~111 (총 {len(TARGET_SEATS)}석)")
    print(f"  조회 주기: {CHECK_INTERVAL}초")
    print("  종료하려면 Ctrl+C 를 누르세요")
    print("=" * 50)

    while True:
        used = get_used_seats()

        if used is not None:
            empty = calc_empty(used)

            if first_run:
                # 처음 실행 시에는 현재 상태만 출력, 알림 없음
                print(f"[{now()}] 초기 상태 확인 — 빈 좌석 {len(empty)}개: {sorted(empty)}")
                prev_empty = empty
                first_run = False
            else:
                # 이번에 새로 빈 좌석 = 이전엔 없었는데 지금 빈 것
                new_empty = empty - prev_empty

                if new_empty:
                    print(f"[{now()}] 🆕 새 빈자리 발생! {sorted(new_empty)}")
                    send_discord(empty, new_empty)
                else:
                    print(f"[{now()}] 변화 없음 — 현재 빈 좌석 {len(empty)}개")

                prev_empty = empty
        else:
            print(f"[{now()}] 조회 실패 — 다음 주기에 재시도")

        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{now()}] 모니터링 종료.")
