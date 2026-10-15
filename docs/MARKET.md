Implementation note: this document records market research and possible differentiators, not a claim that every suggestion shipped. HiringSignal v1 normalizes three public ATS feeds, filters jobs and skips supplied known IDs; it does not infer changed or closed jobs. DocsDelta v1 compares supplied page snapshots and emits per-page chunk changes; it never infers page removals and does not carry state automatically between runs. See each product README for the implemented contract.

# Hai Actor tiếp theo: nhu cầu, khác biệt và giới hạn

Quan sát ngày **15/10/2026**. Nguồn chính: trang Apify Store, API Store/public Actor và tài liệu chính thức của nhà cung cấp. Các số bên dưới là snapshot; trang Store có thể làm tròn hoặc chậm hơn API.

## Khuyến nghị để bắt đầu triển khai

**Ưu tiên DocsDelta (docs/pricing → Markdown + thay đổi có bằng chứng) và HiringSignal (watchlist tuyển dụng Greenhouse/Lever/Ashby).** Cả hai có workflow chạy lại theo lịch, không cần LLM trả phí và có thể cung cấp kết quả hữu ích bằng Python/HTTP. Đây là lựa chọn triển khai dựa trên bằng chứng hiện có, không phải bảo đảm kiếm tiền.

**Shopify catalog/variants là phương án thay thế hợp lý cho HiringSignal**, nếu muốn tập trung ecommerce. Số người dùng hằng tháng của đối thủ catalog trực tiếp đang tương đương, chưa vượt rõ ATS. ATS có lợi thế API công khai được tài liệu hóa; Shopify cần xử lý currency/locale, sitemap và giới hạn variant thật chính xác. Không nên thay ATS chỉ vì một vài Actor multi-ATS mới có ít người dùng: tìm kiếm API trực tiếp cho thấy các đối thủ ATS khác đã có người quay lại.

Không tạo thêm bản sao chỉ đổi tên. Mỗi Actor phải giải quyết một workflow rõ ràng và được smoke test trên cloud trước khi công khai thu phí.

## Bằng chứng sử dụng hiện tại

`totalUsers30Days` được gọi là “người dùng/tháng” trong bảng. **Người dùng, lượt chạy và đánh giá không phải số khách trả tiền hay doanh thu.** Không cộng các hàng vì một người có thể dùng nhiều Actor. Giá minh họa là primary event ở tier **BRONZE**, quy đổi /1.000 kết quả; chưa gồm các event phụ được ghi riêng và có thể đổi sau thời điểm quan sát.

| Actor trực tiếp | Tổng người dùng | Người dùng/tháng | Giá BRONZE quan sát | Phạm vi cần phân biệt |
| --- | ---: | ---: | --- | --- |
| [Website Content Crawler](https://apify.com/apify/website-content-crawler) | 168.836 | 14.247 | Pay per usage | RAG/content nói chung; không phải chỉ monitor |
| [Competitor Marketing Change Monitor](https://apify.com/happitap/competitor-marketing-change-monitor) | 35 | 5 | $2/1.000 page scans + $1/1.000 result rows + $0.25/start | Đối thủ monitor gần hơn, mức dùng nhỏ |
| [Multi-ATS của bovi](https://apify.com/bovi/greenhouse-lever-ashby-job-scraper) | 527 | 114 | $1.485/1.000 jobs + khoảng $0.0000495/start | Đã có 6 ATS, change detection và presets |
| [Greenhouse Jobs API](https://apify.com/fantastic-jobs/greenhouse-jobs-api) | 973 | 142 | $2/1.000 jobs | Truy vấn database do nhà cung cấp thu thập/enrich |
| [Ashby Jobs API](https://apify.com/fantastic-jobs/ashby-jobs-api) | 513 | 99 | $2/1.000 jobs | Database, không phải chỉ đọc URL người dùng đưa |
| [Career Site Job Listing API](https://apify.com/fantastic-jobs/career-site-job-listing-api) | 8.410 | 1.607 | $12/1.000 jobs + $0.0001/start | Rộng hơn: nguồn có sẵn từ nhiều ATS và company enrichment |
| [Career Site Job Listing Feed](https://apify.com/fantastic-jobs/career-site-job-listing-feed) | 1.528 | 273 | $2/1.000 jobs + $0.001/start | Feed database, phạm vi rộng hơn sản phẩm dự kiến |
| [Shopify của autofacts](https://apify.com/autofacts/shopify) | 2.352 | 85 | $1/1.000 products + $0.00005/start | Có event phụ cho collection/recommendation/inventory |
| [Shopify Products của trovevault](https://apify.com/trovevault/shopify-products-scraper) | 728 | 93 | $0.95/1.000 products + $0.00095/start | Có inventory enrichment tính riêng |
| [GEO Technical Audit](https://apify.com/lofomachines/geo-technical-audit) | 117 | 9 | $30/1.000 results + $0.02/start | Một đối thủ audit kỹ thuật; không chứng minh hiệu quả ranking |

Nguồn API để tái kiểm tra số liệu chính xác, không cần dùng token để đọc Actor công khai:

- [Content Crawler metadata](https://api.apify.com/v2/actors/apify~website-content-crawler), [Monitor metadata](https://api.apify.com/v2/actors/happitap~competitor-marketing-change-monitor).
- [Multi-ATS metadata](https://api.apify.com/v2/actors/bovi~greenhouse-lever-ashby-job-scraper), [Greenhouse metadata](https://api.apify.com/v2/actors/fantastic-jobs~greenhouse-jobs-api), [Ashby metadata](https://api.apify.com/v2/actors/fantastic-jobs~ashby-jobs-api).
- [Career API metadata](https://api.apify.com/v2/actors/fantastic-jobs~career-site-job-listing-api), [Career Feed metadata](https://api.apify.com/v2/actors/fantastic-jobs~career-site-job-listing-feed).
- [Shopify autofacts metadata](https://api.apify.com/v2/actors/autofacts~shopify), [Shopify trovevault metadata](https://api.apify.com/v2/actors/trovevault~shopify-products-scraper), [GEO metadata](https://api.apify.com/v2/actors/lofomachines~geo-technical-audit).

Số liệu được đọc từ `stats.totalUsers` và `stats.totalUsers30Days`; pricing đọc `pricingInfos`/`currentPricingInfo` và các tier của event. Không nên lấy một bản ghi giá tương lai làm giá đang active. Các snapshot đọc trong cùng phiên có thể lệch vài người do cập nhật theo thời gian.

## DocsDelta: monitor nội dung để cập nhật knowledge base

**Người dùng mục tiêu:** người vận hành RAG chatbot/knowledge base và nhóm sản phẩm theo dõi tài liệu API hoặc trang pricing. Workflow: đưa URL → lưu baseline → chạy theo ngày → nhận đoạn thay đổi và payload cập nhật/xóa cho index. Người dùng cung cấp danh sách nguồn; Actor không tự biết toàn bộ tài liệu cần theo dõi.

Demand của content/RAG crawler rộng là rõ hơn demand của monitor thuần. Nhưng [Actor chính thức](https://apify.com/apify/website-content-crawler) **đã có incremental crawling**, conditional requests và Markdown. “Chỉ xuất trang đã đổi” không đủ khác biệt; không quảng bá đó là tính năng chưa từng có.

MVP đáng làm:

- Chọn `main`/`article` hoặc CSS selector người dùng chỉ định; bỏ menu/footer; chuyển nội dung thành Markdown, giữ heading, link, bảng và code block.
- So sánh hash nội dung đã chuẩn hóa; trả `new/changed/unchanged`, thời điểm quan sát, source URL và unified diff. Không gọi byte/text diff là hiểu ngữ nghĩa bằng AI.
- Chunk có ID/hash để người vận hành cập nhật index theo đoạn. Có `previousHash`, `currentHash`, chunk được thêm/xóa và phiên bản cấu hình extraction.
- Snapshot có namespace của người dùng, có chế độ reset baseline; lỗi fetch/403/robots không ghi đè baseline tốt. Không suy “trang đã xóa” từ timeout hoặc một crawl chưa hoàn tất; tombstone chỉ khi có bằng chứng thích hợp, ví dụ 404/410 được xác nhận.
- URL công khai, crawl nông, robots mặc định bật; không login, không bypass, không browser trong bản đầu. Nêu rõ trang render bằng JavaScript có thể thiếu nội dung.

HTTP `ETag`, `Last-Modified` và 304 hỗ trợ tiết kiệm request/body nhưng không thay thế normalized hash; server có thể không hỗ trợ hoặc thay đổi header mà nội dung không đổi. Nền tảng kỹ thuật: [HTTP Semantics, RFC 9110](https://www.rfc-editor.org/rfc/rfc9110.html#section-13).

**Giả thuyết giá để đo:** $3/1.000 URL kiểm tra thành công, kể cả `unchanged`; failed/blocked miễn phí. Cần trả trạng thái kiểm tra hữu ích cho mỗi URL và công bố rõ người dùng trả cho lần kiểm tra, không chỉ diff. Chỉ tính khi row đã lưu và không cập nhật snapshot trước khi kết quả đủ điều kiện lưu/charge. Benchmark các trang lớn và nhiều unchanged trước khi bật giá.

## HiringSignal: watchlist tuyển dụng có trạng thái đáng tin

**Người dùng mục tiêu:** niche job board, newsletter tuyển dụng, recruiter nghiên cứu công ty và nhóm nghiên cứu thị trường. Workflow thực tế: theo dõi danh sách board đã biết, lọc role/location/remote, phát hiện tin mới/cập nhật/đóng để cập nhật feed theo lịch.

Nguồn kỹ thuật chính thức:

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html): GET public không cần auth; `/v1/boards/{board_token}/jobs?content=true`. `updated_at` không đồng nghĩa ngày đăng. Pay range có thể cần detail request `pay_transparency=true`.
- [Lever Postings API](https://github.com/lever/postings-api): `/v0/postings/{site}?mode=json`, hỗ trợ host EU, `workplaceType` và `salaryRange` tùy nguồn.
- [Ashby public posting API](https://developers.ashbyhq.com/docs/public-job-posting-api): `/posting-api/job-board/{slug}?includeCompensation=true`. Bỏ `isListed=false`; thiếu field không tự đoán.

Vì đối thủ đã có nhiều ATS và change detection, MVP cần chú trọng tính đúng:

- Schema thống nhất và ID ổn định theo vendor/board/job; giữ dữ liệu nguồn, currency/interval và remote evidence. Remote không tự suy thành “worldwide”; lương thiếu để null, không AI bịa.
- `firstSeen`, `lastSeen`, `new/updated/closed` có snapshot. Chỉ kết luận closed sau khi đã đọc board đầy đủ thành công; board lỗi/capped/timeout không tạo hàng loạt closed giả.
- Filters title/location/remote hoạt động trước billing; không làm regex không giới hạn từ input. Kết quả không khớp và lỗi board là diagnostics miễn phí.
- Có payload lịch/Make/n8n và ví dụ đầu ra delta. Không hứa truy vấn hàng trăm nghìn công ty như đối thủ database; bản đầu chỉ đọc board người dùng cung cấp.

**Giả thuyết giá:** $1.50/1.000 job rows được lưu, không thêm paid start/dataset event trùng. Lượt rerun không thay đổi vẫn tốn platform; nếu có chế độ only-new cần benchmark chi phí watchlist trống trước khi cam kết giá. Hỗ trợ đúng ba nguồn trước khi quảng bá thêm ATS.

## Shopify catalog nếu chọn thay HiringSignal

Sản phẩm hữu ích: nhập domain hoặc product URL → một schema product + variants, SKU/barcode, giá và availability → xuất CSV/JSON, chạy lại theo lịch cho nghiên cứu catalog hoặc theo dõi giá. Khác biệt khả thi là giữ bằng chứng nguồn/currency context, variant CSV riêng và diff giá/availability; **không** gọi availability là tồn kho chính xác.

[Shopify Product Ajax API chính thức](https://shopify.dev/docs/api/ajax/reference/product) xác nhận GET `/{locale}/products/{product-handle}.js`; giá theo presentment currency, xác định currency qua `/{locale}/cart.js`. Response tối đa **250 variants**: không quảng bá lấy tất cả variant của mọi sản phẩm. Locale và format tiền phải giữ riêng, tránh đoán USD. [Sitemap tự sinh](https://help.shopify.com/en/manual/promoting-marketing/seo/find-site-map) giúp khám phá product URL; không coi `/products.json?page=...` là API được bảo đảm chỉ vì nhiều scraper dùng nó.

Rủi ro: catalog theo thị trường/locale, shop private hoặc robots chặn, high-variant products bị cắt, currency khác theo context, JSON endpoint vắng trên headless storefront. Không dùng cart mutation để “suy tồn kho”; không đăng nhập/bypass. Giá đối thủ dưới $1/1.000 sản phẩm làm dư địa giá thấp; phải đo chi phí sitemap + request từng product. Mức $1.50–$2/1.000 product thành công chỉ là giả thuyết nếu đầu ra mang thêm giá trị kiểm chứng được.

## Các hướng chưa nên ưu tiên

**Generic JSON-LD product extractor:** dễ chia sẻ parser và xuất dữ liệu công khai nhưng nhiều trang không có schema đúng/đủ. Hiện chưa có bằng chứng niche trực tiếp mạnh hơn các nguồn trên trong phiên này. Không suy rằng demand Amazon/Temu scraper bằng demand JSON-LD chung.

**GEO technical audit:** có thể báo robots/canonical/schema/headings thật, nhưng demand đối thủ trực tiếp tìm thấy còn nhỏ. Không biến checklist thành điểm “AI rank”, không hứa xuất hiện trong câu trả lời AI. Cần phân biệt indexability kỹ thuật với thứ hạng, citation và doanh thu; chưa nên chọn trước DocsDelta/ATS/Shopify.

## Đo sau khi ra mắt

Theo dõi lỗi nguồn, độ đúng thủ công, chi phí/1.000 kết quả, khách quay lại và lượt chạy từ khách đủ điều kiện trả tiền. Mỗi Actor có một bộ fixture lỗi/partial/currency/state và một cloud run nhỏ có thể xem lại. Owner smoke tests không phải khách mua. Công thức lợi nhuận còn phụ thuộc [chia sẻ doanh thu và chi phí Apify](https://docs.apify.com/actors/publishing/monetize/pricing-and-costs); không suy tiền kiếm được từ số users hay số lần deploy.
