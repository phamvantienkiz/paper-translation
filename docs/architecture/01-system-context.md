# 01 - Bối Cảnh Hệ Thống & Ranh Giới Phạm Vi (System Context & Boundary)

**Tầng tài liệu**: Architecture Layer (Single Source of Truth)  
**Hệ thống**: Paper Translation  
**Phiên bản**: 1.0  
**Ngày cập nhật**: 2026-10-05  
**Trạng thái**: Approved  

---

## 1. Tổng quan Bối cảnh Hệ thống (System Context)

Hệ thống **Paper Translation** là nền tảng tiếp nhận, phân tích bóc tách và dịch thuật tài liệu khoa học chuyên sâu sang tiếng Việt. Hệ thống tương tác với các tác nhân người dùng (Actors) và các hệ thống dịch vụ bên ngoài (External Services) nhằm cung cấp trải nghiệm đọc song ngữ tối ưu mà vẫn bảo toàn nguyên vẹn cấu trúc học thuật.

---

## 2. Định danh các Tác nhân (Actors & External Systems)

### 2.1. Tác nhân con người (Human Actors)
1. **Researcher / Reader (Người nghiên cứu / Độc giả):**
   - Tải lên tệp PDF hoặc dán link arXiv để dịch.
   - Đọc, tra cứu và đối chiếu song ngữ trên giao diện Dual-pane.
   - Chỉnh sửa, duyệt bản dịch từng đoạn và xuất tài liệu kết quả.
2. **System Administrator (Quản trị viên hệ thống):**
   - Quản lý cấu hình hệ sinh thái dịch thuật.
   - Thiết lập, chuẩn hóa và kiểm duyệt các bộ từ điển thuật ngữ (Glossary) hệ thống.

### 2.2. Hệ thống bên ngoài (External Systems)
1. **arXiv Repository & DOI Gateway:**
   - Cung cấp dịch vụ tải tài liệu bài báo công khai và siêu dữ liệu (Metadata) thông qua API hoặc web crawler an toàn.
2. **AI Translation Services & Large Language Models:**
   - Cung cấp năng lực dịch thuật ngữ cảnh chuyên sâu, hiểu biết thuật ngữ khoa học và xử lý ngôn ngữ tự nhiên.

---

## 3. Sơ đồ Ranh giới Hệ thống & Use Case (System Boundary & Use Cases)

Sơ đồ thể hiện toàn bộ các chức năng cốt lõi nằm trong ranh giới của hệ thống Paper Translation và sự tương tác với các tác nhân bên ngoài:

```mermaid
flowchart LR
    subgraph Actors ["Tác nhân (Actors)"]
        User["👤 Nhà nghiên cứu / Độc giả"]
        Admin["👨‍💼 Quản trị viên"]
        Arxiv["🌐 arXiv / DOI Gateway"]
        LLM["🤖 AI Translation Engine"]
    end

    subgraph SystemBoundary ["Ranh giới Hệ Thống: Paper Translation"]
        UC1["(Tiếp nhận bài báo: Upload PDF / URL)"]
        UC2["(Bóc tách cấu trúc & Bảo toàn LaTeX)"]
        UC3["(Áp dụng Glossary thuật ngữ)"]
        UC4["(Thực thi dịch thuật chuyên sâu)"]
        UC5["(Đọc đối chiếu song ngữ Dual-pane)"]
        UC6["(Chỉnh sửa & Duyệt bản dịch từng đoạn)"]
        UC7["(Xuất bản dịch Markdown / PDF)"]
        UC8["(Quản trị bộ từ điển Glossary)"]

        UC1 -.->|<<include>>| UC2
        UC2 -.->|<<include>>| UC3
        UC3 -.->|<<include>>| UC4
        UC4 -.->|<<include>>| UC5
        UC5 -.->|<<extend>>| UC6
        UC5 -.->|<<extend>>| UC7
    end

    User --> UC1
    User --> UC5
    User --> UC8
    Admin --> UC8

    UC1 <-->|Tải bài báo & Metadata| Arxiv
    UC4 <-->|Dịch thuật ngữ cảnh| LLM
```

---

## 4. Dòng chảy nghiệp vụ mức cao (High-Level Process Flow)

Dòng dữ liệu từ khi tài liệu được đưa vào hệ thống cho tới khi hoàn tất bản dịch:

```mermaid
flowchart TD
    Start([Người dùng bắt đầu]) --> Choice{Phương thức nhập?}
    Choice -- Upload File --> IngestPDF[Nhận tệp PDF cục bộ]
    Choice -- Nhập Liên kết --> IngestURL[Tải PDF & Metadata từ arXiv]
    
    IngestPDF --> Parse[Bóc tách cấu trúc bài báo]
    IngestURL --> Parse
    
    Parse --> IsolateMath[Cô lập công thức toán LaTeX & Giữ nguyên bảng/hình]
    IsolateMath --> SegmentDoc[Phân đoạn văn bản logic]
    SegmentDoc --> ApplyGlossary[Khớp & Áp dụng Glossary thuật ngữ]
    ApplyGlossary --> Translate[Gọi AI Engine dịch ngữ cảnh sang Tiếng Việt]
    Translate --> Reconstruct[Ghép nối phân đoạn & Re-inject công thức LaTeX]
    Reconstruct --> RenderDual[Hiển thị giao diện đọc song ngữ Dual-Pane]
    
    RenderDual --> Action{Thao tác người dùng}
    Action -- Cuộn đọc --> ScrollSync[Cuộn đồng bộ hai cột]
    Action -- Chỉnh sửa --> EditSeg[Sửa trực tiếp phân đoạn bản dịch]
    Action -- Xuất bản --> Export[Xuất file Markdown / PDF]
    
    ScrollSync --> RenderDual
    EditSeg --> RenderDual
    Export --> Finish([Hoàn thành])
```

---

## 5. Ranh giới Trách nhiệm & Bất biến Hệ thống (Architectural Invariants)

1. **Bất biến về công thức toán:** Không một tiến trình xử lý ngôn ngữ tự nhiên nào được phép ghi đè, sửa đổi hoặc làm mất cú pháp của các khối công thức toán học (`$ ... $` hoặc `$$ ... $$`).
2. **Bất biến về tính đối xứng song ngữ:** Mọi văn bản đã dịch phải duy trì định danh phân đoạn (Segment ID) liên kết ánh xạ 1-1 với phân đoạn gốc để đảm bảo tính năng cuộn đồng bộ và biên tập chính xác.
3. **Bất biến về kiểm soát Glossary:** Thuật ngữ đã được quy định trong Glossary bắt buộc phải được ưu tiên chuẩn hóa trong câu dịch, ngăn chặn sự dịch sai lệch ngẫu nhiên.
