# Kế hoạch tìm người dùng đầu tiên trong 7 ngày

Mục tiêu thử nghiệm: **3 người ngoài tài khoản chủ dự án thử nguồn của họ và
ít nhất 1 người quay lại**. Theo dõi người trả phí riêng; không hứa rằng phải có
doanh thu trong 7 ngày. Ưu tiên DocsDelta trong thử nghiệm này.

## Hôm nay: làm trang sản phẩm dễ hiểu

1. Tải `assets/brand/icon-512.png` lên Publishing → Display information của
   [DocsDelta](https://console.apify.com/actors/02Xe4XI3SVfP6CIka/publication).
   File đã có sẵn; API công khai vẫn cho thấy chưa có logo khi kiểm tra.
2. Mở [hướng dẫn hai trang](FIRST_RUN.md) và xem ảnh đầu ra. Chạy trên nguồn của
   người thử khi cần kiểm chứng; không chạy lặp chỉ để tăng số lượt dùng.
3. Đọc [bài giới thiệu](LAUNCH_POSTS.md), sửa cách xưng hô nếu cần và tự đăng
   một bản lên trang cá nhân hoặc thread cho phép. Tác giả đã được công khai
   trong bản nháp; chưa có bài hay tin nhắn nào được gửi tự động.

## Ngày 2–3: tìm đúng vấn đề

Chọn những cuộc thảo luận có người đang xây chatbot tài liệu hoặc cập nhật RAG.
Hỏi họ đang lấy dữ liệu ở đâu, cập nhật bằng cách nào và lỗi nào khiến họ phải
sửa tay. Chỉ giới thiệu khi phù hợp với câu hỏi và nội quy; đưa ví dụ đầu ra và
công khai mình là tác giả. Không gửi tin hàng loạt, không chỉ thả đường dẫn.

Mời người tự nguyện thử 1–2 URL công khai họ đang xử lý. Ghi lại vấn đề thực tế,
không xin đánh giá 5 sao hoặc đổi quà để lấy review. Đừng hứa xử lý được trang
JavaScript, PDF hoặc nguồn cần đăng nhập vì phiên bản hiện tại không hỗ trợ.

## Ngày 4–5: sửa một chỗ gây khó nhất

Nếu nhiều người cùng mắc ở chọn vùng nội dung, truyền snapshot hay đưa chunks
vào index, ưu tiên giải quyết đúng bước đó và cập nhật hướng dẫn. Hỏi người thử
có muốn tiếp tục dùng với dữ liệu thật của họ theo giá công khai không. Đây là
phản hồi mua hàng, không phải lời mời tạo tài khoản hay lượt chạy giả.

## Ngày 6–7: quyết định bằng số liệu

Ghi trong `acquisition-log.csv`; để trống số chưa đo được. Xem Insights →
Acquisition/Monetization cho truy cập và lượt dùng có dữ liệu thực. Không cộng
owner test vào người dùng mới; free users và paying users là hai nhóm riêng.

- Không có lượt vào: kiểm tra thông điệp, nơi chia sẻ và hình minh họa.
- Có lượt vào nhưng không chạy: hỏi về độ rõ ràng, giá, tài khoản Apify hoặc
  đầu vào đang gây cản trở. Đọc phản hồi trước khi kết luận nguyên nhân.
- Có người thử nhưng không quay lại: kiểm tra chất lượng dữ liệu và bước tích
  hợp. Chưa cần thêm tính năng nếu chưa biết lỗi hay nhu cầu nào.
- Có người quay lại nhưng không trả phí: tìm hiểu quy mô/cadence sử dụng và
  điều kiện tính doanh thu; không gọi lượt miễn phí là tiền kiếm được.

Chưa cần ngân sách quảng cáo cho thử nghiệm này. Ngân sách chạy thử chỉ dùng
khi kiểm chứng dữ liệu thật hoặc sửa lỗi cụ thể; đặt maximum cost cho từng run.

## Nguồn và giới hạn

[Apify marketing checklist](https://docs.apify.com/academy/actor-marketing-playbook/promote-your-actor/checklist)
và [Actor quality score](https://docs.apify.com/actors/publishing/quality-score).
Đây là kế hoạch thử nghiệm do dự án đặt ra, không phải cam kết hiệu quả từ Apify.
