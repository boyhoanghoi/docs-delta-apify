# Ready-to-review launch posts

Prepared 16 October 2026. These are drafts; none has been posted or sent.
Both posts disclose the creator's connection and the current paid model.

## English: personal profile or an allowed project thread

I built DocsDelta for developers who refresh documentation in a RAG index or an
AI coding assistant's knowledge base.

It takes public HTML pages and returns cleaned Markdown, source-linked chunks,
and NEW/UPDATED/UNCHANGED page states. Supply the previous run's snapshot to get
chunk IDs to upsert or remove after a successful refetch. Failed pages preserve
their old baseline; the tool never guesses that a whole page was deleted.

An owner test read 2 documentation pages into 37 chunks. A repeat check with the
same snapshot and changedOnly enabled returned no saved changes. That is one
sample, not a customer result or a speed benchmark.

It uses Python and HTTP extraction, not an LLM. It does not generate embeddings
or run a chatbot. The configured price is $3 per 1,000 saved page checks; chunks
are included. Default saved unchanged checks are billed; changedOnly filters
them without a page event. Check Apify's Pricing tab for current terms.

I'm looking for feedback from 3 builders already indexing documentation. Try
1–2 public URLs you use and tell me which output you would still need to fix by
hand. Please do not share private URLs or credentials.

Two-page walkthrough: https://github.com/boyhoanghoi/docs-delta-apify/blob/main/docs/FIRST_RUN.md

Actor: https://apify.com/reliable_quatrain/website-markdown-rag-change-feed

## Tiếng Việt: trang cá nhân hoặc nhóm cho phép giới thiệu sản phẩm

Mình vừa làm DocsDelta cho người đang đưa tài liệu website vào chatbot hoặc kho
dữ liệu AI. Khi tài liệu thay đổi, công cụ trả Markdown, các đoạn có nguồn và
danh sách ID đoạn cần cập nhật. Trang đọc lỗi giữ lại baseline cũ, không tự kết
luận dữ liệu đã bị xóa.

Lần thử trên tài khoản của mình: 2 trang tài liệu tạo 37 đoạn; đọc lại cùng
snapshot ở chế độ chỉ lấy thay đổi thì không lưu thêm trang nào. Đây là ví dụ
kiểm thử, chưa phải kết quả từ khách hàng.

Actor tính $3/1.000 trang được lưu, đã gồm các đoạn con. Mặc định trang kiểm tra
thành công không đổi vẫn được lưu và tính phí; changedOnly bỏ qua chúng. Công cụ
đọc HTML, chưa chạy JavaScript hay tự tạo chatbot/embedding. Hệ thống gọi cần
truyền snapshot của lần trước vào lần sau.

Mình muốn xin phản hồi từ 3 bạn đang làm chatbot tài liệu: thử 1–2 URL công khai
bạn đang dùng và cho biết đầu ra còn phải sửa tay phần nào. Không cần gửi tài
liệu riêng tư hoặc token.

Hướng dẫn: https://github.com/boyhoanghoi/docs-delta-apify/blob/main/docs/FIRST_RUN.md

Dùng Actor: https://apify.com/reliable_quatrain/website-markdown-rag-change-feed

## Where to use these drafts

- Your own LinkedIn/Facebook profile: choose the language appropriate to your
  audience. Do not claim existing customers or measured time savings.
- [r/ChatGPTCoding weekly self-promotion thread](https://www.reddit.com/r/ChatGPTCoding/comments/1x3vw47/weekly_self_promotion_thread/), checked on 16 October 2026: the thread permits AI-assisted-coding projects with context and creator disclosure. Recheck that it is open and read its current rules before posting. Use the latest permitted thread if this one has closed. One useful post is enough; do not repeat the same promotion without meaningful changes.
- [Built with n8n](https://community.n8n.io/t/about-the-built-with-n8n-category/3411) is for projects actually built with n8n. This repository currently provides a workflow guide, not a tested imported n8n workflow, so do not present DocsDelta as such a showcase yet.

The [Apify marketing checklist](https://docs.apify.com/academy/actor-marketing-playbook/promote-your-actor/checklist)
recommends useful walkthroughs and demo assets. The
[Actor quality guide](https://docs.apify.com/actors/publishing/quality-score)
explains visibility signals; neither promises visitors or a ranking.
