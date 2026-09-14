# Tổng kết Nhiệm vụ Nhóm trưởng (Leader Contribution Report)

- **Họ và Tên:** Nguyễn Ngọc Bảo
- **MSSV:** 2A202602951
- **GitHub Username:** KeepGoing132
- **Vai trò:** Nhóm trưởng (Team Leader)
- **Repository:** https://github.com/KeepGoing132/K4-Day04-KeDocHanh
- **Các nhánh phụ trách:** `main`, `Nguyen_Ngoc_Bao`, `Nguyen_Ngoc_Bao_2A202602951`

---

## 1. Chi tiết thực hiện 4 Nhiệm vụ chính (Tasks)

### Task 1: Thiết kế kiến trúc tổng thể và điều phối quy trình Eval
- Phân tích toàn bộ starter kit, luồng thực thi trong `agent.py`, `chat.py`, `run_eval.py` và adapter các model providers.
- Thiết lập quy trình lặp khoa học dựa trên evidence:
  $$\text{v0 (Baseline)} \longrightarrow \text{v1 (Routing \& Clarify)} \longrightarrow \text{v2 (Multi-turn \& Parallel)} \longrightarrow \text{v3 (Safety \& Boundaries)}$$
- Xây dựng cấu trúc thư mục lưu trữ snapshot `starter_v0/artifacts/versions/` để mọi phiên bản đều có thể audit và tái lập độc lập.

---

### Task 2: Prompt Engineering qua 4 phiên bản (`system_prompt.md`)
Tối ưu hóa có cơ sở khoa học từ phân tích thất bại (Failure Traces) trên bộ `eval_base.json`:

1. **Phiên bản v0 (Baseline):**
   - *Thực trạng:* Prompt sơ khai, thiếu định hướng vai trò và quy tắc chọn tool.
   - *Hạn chế:* Model thường xuyên tự đoán mã máy (như tự gán `LT-204`), chọn nhầm `inspect_device` cho dịch vụ VPN dùng chung, và tự ý gọi ticket mà không xin phép.
   - *Accuracy:* `0.5333`.

2. **Phiên bản v1 (`artifacts/versions/v1_system_prompt.md`):**
   - *Giả thuyết 1:* Phân định ranh giới giữa dịch vụ dùng chung và thiết bị cá nhân, kết hợp quy tắc cấm đoán ID sẽ nâng cao đáng kể routing accuracy.
   - *Cải tiến:*
     - Bổ sung bảng phân loại: dịch vụ dùng chung (VPN, Email, SSO, Wi-Fi, Printing) bắt buộc gọi `check_service_status`; thiết bị phần cứng cụ thể (`LT-xxx`, `DT-xxx`) bắt buộc gọi `inspect_device`.
     - Đưa ra nguyên tắc vàng: **"Never Guess Identifiers"** — khi thiếu Asset ID hoặc Employee ID, bắt buộc gọi `clarify(response_type="text")`.
   - *Kết quả:* Accuracy tăng vọt lên `0.7667`.

3. **Phiên bản v2 (`artifacts/versions/v2_system_prompt.md`):**
   - *Giả thuyết 2:* Thiết lập quy tắc "Latest intent wins", hỗ trợ gọi song song và định dạng báo cáo không refetch sẽ giải quyết triệt để các ca multi-turn.
   - *Cải tiến:*
     - Ưu tiên lượt thoại mới nhất: Thông tin sửa đổi ở lượt sau (ví dụ đổi máy từ `LT-204` sang `LT-318`) phải ghi đè thông tin cũ.
     - Hủy yêu cầu (Cancellation): Khi user yêu cầu dừng/hủy, không gọi tool và chỉ xác nhận bằng lời.
     - Hỗ trợ gọi song song (Parallel Tool Invocations) khi yêu cầu cần kiểm tra cả service lẫn máy con, hoặc so sánh 2 môi trường.
     - Ranh giới định dạng: Khi findings đã có sẵn, chỉ gọi `format_incident_report`.
   - *Kết quả:* Multiturn accuracy đạt 100%, tổng accuracy nâng lên `0.9000`.

4. **Phiên bản v3 (`artifacts/versions/v3_system_prompt.md` & `tools.yaml`):**
   - *Giả thuyết 3:* Thiết lập ranh giới an toàn nghiêm ngặt cho write actions và quyền riêng tư dữ liệu external search sẽ đưa agent đạt chuẩn an toàn production.
   - *Cải tiến:*
     - Action confirmation boundary: Chỉ gọi `create_ticket` khi có xác nhận rõ ràng `confirmed=true`. Bất kỳ thay đổi nào về priority hay nội dung đều làm vô hiệu hóa xác nhận cũ $\rightarrow$ bắt buộc hỏi lại `clarify(response_type="yes_no")`.
     - Tuyệt đối cấm đưa password, token, API key, MFA/OTP vào ticket payload.
     - Data privacy boundary: Khi tìm kiếm web qua `search_device_info`, chỉ gửi hãng và tên model công khai, tuyệt đối không gửi mã nội bộ ra ngoài.
   - *Kết quả:* Accuracy đạt `0.9667`, vượt qua cả extension và adversarial suites.

---

### Task 3: Thiết kế 5 Single-Turn Test Cases (`G01` – `G05` trong `eval_group.json`)
Trực tiếp thiết kế và viết 5 ca kiểm thử độc lập cho nhóm trưởng, bao phủ đầy đủ các kỹ năng cốt lõi:
- **`G01_missing_asset_clarify`:** Người dùng báo màn hình laptop chập chờn nhưng không đưa mã máy $\rightarrow$ Agent phải gọi `clarify(response_type="text")`, không được tự đoán ID.
- **`G02_parallel_wifi_service_device`:** Sự cố Wi-Fi văn phòng cần kiểm tra cả tình trạng Wi-Fi production và card mạng của máy LT-318 $\rightarrow$ Gọi đồng thời cả `check_service_status` và `inspect_device`.
- **`G03_policy_vs_kb_boundary`:** Hỏi về quy định sử dụng công cụ AI bên ngoài $\rightarrow$ Định tuyến chính xác vào `policy(policy_area="external_tools")`, không gọi KB kỹ thuật.
- **`G04_format_only_incident`:** Yêu cầu tổng hợp các findings có sẵn thành báo cáo tóm tắt $\rightarrow$ Gọi duy nhất `format_incident_report(template="brief")`, không kiểm tra lại thiết bị.
- **`G05_out_of_scope_travel`:** Yêu cầu tư vấn lịch trình du lịch cá nhân $\rightarrow$ Từ chối lịch sự ngoài phạm vi hỗ trợ, `no_tool`.

---

### Task 4: Tổng hợp Metrics, Ghi `version_log.csv` & Kiểm tra Toàn vẹn
- Tính toán chính xác mã SHA256 cho từng file prompt và tools:
  - `v0`: `v0+p233ec2cecfdf+teb3e2243f237`
  - `v1`: `v1+pc188ab310564+teb3e2243f237`
  - `v2`: `v2+pd083c9fdc3f2+teb3e2243f237`
  - `v3`: `v3+pbc24a1d2beaa+t784840b74f9f`
- Ghi nhật ký chuẩn xác vào [`starter_v0/artifacts/version_log.csv`](file:///e:/D/learn_AI/K4-Day04-Prompt-Engineering-Tool-Calling-Labs/starter_v0/artifacts/version_log.csv) với đầy đủ giả thuyết và số liệu đo lường.
- Hoàn thiện tài liệu tổng hợp và kiểm tra chéo trước khi đưa lên repository chính.
