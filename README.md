# tele-stock-bot

Mỗi ngày giao dịch, sau khi đóng phiên (15:15 giờ Việt Nam), gửi một tin **tổng kết** các mã yêu thích qua Telegram. Dữ liệu lấy từ Yahoo Finance (mã dạng `VNM.VN`).

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
4. Workflow `.github/workflows/daily-summary.yml` tự chạy 15:15 VN (T2–T6); có thể bấm *Run workflow* để chạy thử.

## Chạy liên tục (VPS / Botkeep…)
Host không có cron thì chạy `python -m stockbot --daemon` (tự ngủ đến 15:15 giờ VN mỗi ngày T2–T6 rồi gửi). Cấu hình qua biến môi trường `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## Chạy tay
```bash
pip install -r requirements.txt
python -m stockbot --dry-run --force        # chỉ in ra màn hình
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python -m stockbot
```
Test: `python -m unittest discover -s tests`. Biến tuỳ chọn: xem `.env.example`.

## Lưu ý
- Yahoo Finance gần như chỉ có mã sàn HOSE; mã HNX/UPCoM thường trả 404 và bị liệt kê ở dòng "Không lấy được".
- Cron của GitHub Actions có thể trễ vài phút.
