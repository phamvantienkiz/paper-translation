from typing import Dict

# Từ điển chuyên ngành Công nghệ thông tin & Trí tuệ nhân tạo (IT & AI)
IT_AI_GLOSSARY: Dict[str, str] = {
    "attention mechanism": "cơ chế chú ý (attention mechanism)",
    "self-attention": "tự chú ý (self-attention)",
    "multi-head attention": "chú ý đa đầu (multi-head attention)",
    "transformer": "Transformer",
    "encoder": "bộ mã hóa (encoder)",
    "decoder": "bộ giải mã (decoder)",
    "feed-forward network": "mạng truyền thẳng (feed-forward network)",
    "feedforward": "truyền thẳng (feedforward)",
    "backpropagation": "lan truyền ngược (backpropagation)",
    "gradient descent": "hạ độ dốc (gradient descent)",
    "stochastic gradient descent": "hạ độ dốc ngẫu nhiên (SGD)",
    "loss function": "hàm mất mát (loss function)",
    "overfitting": "quá khớp (overfitting)",
    "underfitting": "dưới khớp (underfitting)",
    "learning rate": "tốc độ học (learning rate)",
    "batch size": "kích thước batch (batch size)",
    "epoch": "kỷ nguyên (epoch)",
    "latent space": "không gian tiềm ẩn (latent space)",
    "fine-tuning": "tinh chỉnh (fine-tuning)",
    "pre-trained": "tiền huấn luyện (pre-trained)",
    "zero-shot": "zero-shot",
    "few-shot": "few-shot",
    "large language model": "mô hình ngôn ngữ lớn (LLM)",
    "large language models": "các mô hình ngôn ngữ lớn (LLMs)",
    "embedding": "nhúng (embedding)",
    "embeddings": "các vector nhúng (embeddings)",
    "residual connection": "kết nối thặng dư (residual connection)",
    "residual block": "khối thặng dư (residual block)",
    "layer normalization": "chuẩn hóa tầng (layer normalization)",
    "batch normalization": "chuẩn hóa batch (batch normalization)",
    "regularization": "chính quy hóa (regularization)",
    "dropout": "dropout",
    "activation function": "hàm kích hoạt (activation function)",
    "convolutional neural network": "mạng nơ-ron tích chập (CNN)",
    "recurrent neural network": "mạng nơ-ron hồi quy (RNN)",
    "tokenizer": "bộ tách từ (tokenizer)",
    "tokenization": "tách từ (tokenization)",
    "benchmark": "bộ tiêu chuẩn đánh giá (benchmark)",
    "ablation study": "nghiên cứu loại trừ (ablation study)",
    "state-of-the-art": "hiện đại nhất (state-of-the-art / SOTA)",
    "ground truth": "dữ liệu chuẩn thực tế (ground truth)",
    "hyperparameter": "siêu tham số (hyperparameter)",
    "inference": "suy luận (inference)",
}


def build_system_instruction() -> str:
    """Tạo prompt hệ thống chuẩn hóa hướng dẫn dịch thuật cho mô hình LLM."""
    glossary_sample = "\n".join(
        [f"- {k} -> {v}" for k, v in list(IT_AI_GLOSSARY.items())[:15]]
    )
    return (
        "Bạn là chuyên gia dịch thuật tài liệu khoa học chuyên ngành Công nghệ Thông tin và Trí tuệ Nhân tạo (IT & AI).\n"
        "Nhiệm vụ của bạn là dịch các đoạn văn bản khoa học từ tiếng Anh sang tiếng Việt với văn phong học thuật chuẩn mực.\n\n"
        "CÁC QUY TẮC BẮT BUỘC:\n"
        "1. BẢO TOÀN NGUYÊN VẸN CÁC TOKEN TOÁN HỌC: Mọi chuỗi có dạng <<<MATH_TOKEN_XXXX>>> (ví dụ <<<MATH_TOKEN_0001>>>) "
        "PHẢI được giữ nguyên 100% không đổi, không được xóa, không thêm bớt ký tự, không dịch.\n"
        "2. BẢO TOÀN THUẬT NGỮ CHUYÊN NGÀNH: Áp dụng thuật ngữ chuẩn tiếng Việt kèm từ gốc tiếng Anh trong ngoặc đơn nếu cần:\n"
        f"{glossary_sample}\n"
        "3. ĐỊNH DẠNG: Giữ nguyên định dạng Markdown (tiêu đề, danh sách, bảng Markdown).\n"
        "4. CHỈ TRẢ VỀ NỘI DUNG ĐÃ DỊCH, không kèm lời mở đầu hoặc giải thích thêm."
    )
