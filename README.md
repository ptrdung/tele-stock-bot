# tele-stock-bot

Mỗi ngày giao dịch, sau khi đóng phiên (15:15 và 15:30 giờ Việt Nam), gửi tin **tổng kết** các mã yêu thích qua Telegram. Dữ liệu lấy từ Yahoo Finance (mã dạng `VNM.VN`).

## Nội dung tin
- Mục **Cần chú ý**: các mã chạm ngưỡng cảnh báo.
- Bảng toàn bộ mã: giá đóng cửa, % thay đổi, RSI(14), sắp từ giảm mạnh nhất.

| Cảnh báo | Điều kiện |
|---|---|
| RSI | RSI(14, Wilder, nến ngày) < 30 |
| Chạm sàn | Giá ≤ giá sàn = tham chiếu × (1 − biên độ), làm tròn lên theo bước giá. Biên độ: HOSE 7%, HNX 10%, UPCoM 15% |
| Giảm mạnh | Giảm ≥ 6% so với giá tham chiếu (phiên trước) |

Ngày nghỉ (cuối tuần, lễ) không có phiên mới thì script không gửi gì.

## Cài đặt (GitHub Actions)
1. Tạo bot qua @BotFather để lấy token; lấy chat id (nhắn bot rồi mở `https://api.telegram.org/bot<TOKEN>/getUpdates`).
2. Repo → Settings → Secrets and variables → Actions, thêm `TELEGRAM_BOT_TOKEN` và `TELEGRAM_CHAT_ID` (nhiều chat: cách nhau bởi dấu phẩy).
3. Sửa `watchlist.txt` để chọn mã theo dõi.
4. Workflow `.github/workflows/daily-summary.yml` tự chạy 15:15 và 15:30 VN (T2–T6); có thể bấm *Run workflow* để chạy thử.

## Tra cứu mã
Khi chạy `--daemon`, nhắn cho bot một mã (`FPT`) hoặc `/s FPT` để nhận: giá, tham chiếu/trần/sàn, mở/cao/thấp, khối lượng so với TB20, RSI(14), MA20/MA50, hiệu suất 1 tuần/1 tháng/3 tháng/từ đầu năm, đỉnh–đáy 52 tuần, kèm biểu đồ 3 tháng. Bot chỉ trả lời các chat trong `TELEGRAM_CHAT_ID`. Trong nhóm (privacy mode bật) dùng `/s FPT`.

matplotlib chỉ được nạp ở lần tra cứu đầu tiên: bot chiếm ~30 MB RAM khi chờ, ~100–120 MB sau khi đã vẽ biểu đồ.

## Chạy liên tục (VPS / Botkeep…)
Host không có cron thì chạy `python -m stockbot --daemon`: nhận lệnh tra cứu và tự gửi tổng kết lúc 15:15 và 15:30 giờ VN mỗi ngày T2–T6 (đổi giờ bằng `SEND_TIMES`). Cấu hình qua biến môi trường `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` hoặc file `.env`. Chỉ chạy **một** tiến trình `--daemon` cho mỗi bot token (Telegram không cho hai nơi cùng nhận tin).

## Chạy tay
```bash
pip install -r requirements.txt
python -m stockbot --dry-run --force        # chỉ in ra màn hình
python -m stockbot --lookup FPT --dry-run   # in tin tra cứu, lưu biểu đồ FPT.png
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python -m stockbot
```
Test: `python -m unittest discover -s tests`. Biến tuỳ chọn: xem `.env.example`.

## Lưu ý
- Yahoo Finance gần như chỉ có mã sàn HOSE; mã HNX/UPCoM thường trả 404 và bị liệt kê ở dòng "Không lấy được".
- Cron của GitHub Actions có thể trễ vài phút.
