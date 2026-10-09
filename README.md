# tele-stock-bot

Bot Telegram cảnh báo cổ phiếu Việt Nam, lấy dữ liệu từ Yahoo Finance (mã dạng `VNM.VN`).

## Cảnh báo
| Loại | Điều kiện |
|---|---|
| `rsi` | RSI(14, Wilder, nến ngày) < 30 |
| `floor` | Giá ≤ giá sàn = tham chiếu × (1 − biên độ), làm tròn lên theo bước giá. Biên độ: HOSE 7%, HNX 10%, UPCoM 15% |
| `drop` | Giảm ≥ 6% so với giá tham chiếu (phiên trước) |

Mỗi loại cảnh báo chỉ gửi 1 lần cho mỗi mã / người dùng / ngày giao dịch. Mặc định chỉ quét trong giờ giao dịch (T2–T6, 9:00–15:15 giờ VN), mỗi 10 phút.

## Chạy
```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...   # tạo bot qua @BotFather
python -m stockbot
```
Biến tuỳ chọn: xem `.env.example`. Test: `python -m unittest discover -s tests`.

## Lệnh
`/pick` chọn từ VN30 · `/add VNM HPG` · `/remove VNM` · `/list` · `/check` · `/help`

## Lưu ý
- Yahoo Finance gần như chỉ có mã sàn HOSE; mã HNX/UPCoM thường trả 404 và `/add` sẽ từ chối.
- Dữ liệu Yahoo có thể trễ so với bảng giá thực tế; "giá hiện tại" là giá đóng cửa của nến ngày mới nhất.
