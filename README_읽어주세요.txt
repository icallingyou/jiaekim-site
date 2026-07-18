김지애 작가 사이트 v2 — 사용 안내

[올리는 법 · GitHub Pages]
1) github.com 로그인 → New repository (예: jiaekim-site, Public) 생성
2) "uploading an existing file" 클릭 → 이 폴더 안의 내용물 전체(index.html, CNAME, images 폴더)를 드래그 → Commit
3) Settings → Pages → Branch: main /(root) 저장
4) 같은 화면 Custom domain에 jiaekim.com 입력 → 이후 Squarespace DNS에 A레코드 4개 + CNAME(www) 추가 (이전에 드린 표 그대로)
※ 다른 도메인을 쓰기로 했다면 CNAME 파일 내용만 그 주소로 바꾸세요.

[나중에 교체할 자리 — index.html 안에 ★ 표시로 주석해 두었습니다]
- 뉴스레터: 스티비/Beehiiv 가입 후 form action 주소 교체 (그 전까지는 메일 앱으로 연결됨)
- 샵: 검로드/코파이 링크 생기면 '준비 중' 버튼을 링크 버튼으로 교체
- 전시 날짜: 8월 일정 확정되면 '일정 추후 공지' 두 곳(히어로 카드, 전시 목록) 수정

[그림 한 점 추가하는 법]
1) 사진을 images/ 폴더에 넣기 (긴 변 1600px 정도 권장)
2) index.html에서 <figure class="art"> 블록 하나를 복사해 파일명·제목·연도·크기만 수정
- 또는 저(Claude)에게 사진과 정보를 주시면 수정본을 만들어 드립니다.
