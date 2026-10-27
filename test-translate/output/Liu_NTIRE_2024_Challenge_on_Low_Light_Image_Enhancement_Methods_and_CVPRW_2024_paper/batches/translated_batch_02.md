## 4. Các Phương pháp và Đội thi (Challenge Methods and Teams)

### 4.1. SYSU-FVL-T2

Hình 1. Mạng xương sống (backbone network) được sử dụng trong phương pháp của chúng tôi. (Được tái hiện từ ESDNet [75])

**Mô tả:** Như được minh họa trong Hình 1, ESDNet-L [75] được sử dụng làm mạng xương sống (backbone) trong phương pháp đề xuất của chúng tôi cho bài toán tăng cường ảnh thiếu sáng. Mạng xương sống chủ yếu bao gồm một mạng bộ mã hóa - bộ giải mã (encoder-decoder) ở ba tỷ lệ đặc trưng với các kết nối tắt (skip-connections). Các tỷ lệ đặc trưng khác nhau được tạo ra bằng cách áp dụng phép nội suy song tuyến tính (bilinear interpolation). Ở mỗi tỷ lệ, các Mô-đun Nhận biết Tỷ lệ Căn chỉnh Ngữ nghĩa (Semantic-Aligned Scale-Aware Modules - SAM) được xếp chồng lên nhau để nâng cao khả năng của mô hình trong việc xử lý các biến đổi về tỷ lệ. SAM kết hợp một mô-đun trích xuất ngữ cảnh kim tự tháp (pyramid context extraction module) và một mô-đun hợp nhất động xuyên tỷ lệ (cross-scale dynamic fusion module) để hợp nhất có chọn lọc các đặc trưng đa tỷ lệ.

Hơn nữa, đối với quá trình huấn luyện mạng, hàm mất mát (loss function) <<<MATH_TOKEN_0013>>> được thiết lập cho các đầu ra ở ba tỷ lệ <<<MATH_TOKEN_0014>>>:

$$L_{\text{total}} = \sum_{i=1}^{3} L_C(I_i, \hat{I}_i) + \lambda \cdot L_P(I_i, \hat{I}_i), \quad (1)$$

trong đó <<<MATH_TOKEN_0015>>> được thiết lập là <<<MATH_TOKEN_0016>>> đại diện cho ảnh dữ liệu chuẩn thực tế (ground truth), <<<MATH_TOKEN_0017>>> đại diện cho ảnh được tăng cường, <<<MATH_TOKEN_0018>>> đại diện cho mất mát Charbonnier (Charbonnier loss) <<<MATH_TOKEN_0019>>> và <<<MATH_TOKEN_0020>>> đại diện cho mất mát cảm nhận (perceptual loss) sử dụng mô hình VGG19 đã được huấn luyện trước (pretrained) [66].

**Cài đặt thực nghiệm (Implementation):** Phương pháp đề xuất được xây dựng dựa trên Python 3.8 và thử nghiệm được tiến hành trên một GPU NVIDIA RTX A6000 (49G). Được truyền cảm hứng từ MIRNet-v2 [79], chúng tôi áp dụng chiến lược huấn luyện lũy tiến (progressive training strategy). Mô hình được huấn luyện trong 150.000 bước lặp (iterations) từ đầu (from scratch) và được tối ưu hóa bằng thuật toán Adam [41]. Trong suốt quá trình huấn luyện, ở giai đoạn đầu tiên, kích thước batch (batch size) được đặt là 8, và chúng tôi cắt ngẫu nhiên các mảnh ảnh vuông có kích thước 720 để huấn luyện. Sau đó, sau 46.000, 32.000, 24.000, 18.000 và 18.000 bước lặp, kích thước batch giảm dần lần lượt xuống 4, 4, 2, 2 và 1. Độ dài cạnh của các mảnh ảnh vuông được đặt thành 1024, 1024, 1280, 1280 và 1600 cho các giai đoạn tương ứng. Tốc độ học (learning rate) ban đầu được thiết lập là <<<MATH_TOKEN_0021>>> và được điều chỉnh theo lịch trình giảm dần cosine tuần hoàn (cyclic cosine annealing) [52]. Trong giai đoạn kiểm thử, toàn bộ hình ảnh thiếu sáng được đưa vào mạng và thu được trực tiếp hình ảnh tăng cường. Kích thước batch khi kiểm thử được đặt là 1.

### 4.2. Retinexformer

trong đó đại diện cho phép nhân theo từng phần tử (element-wise multiplication). Tuy nhiên, giả định không bị suy giảm (corruption-free) này không phù hợp với các cảnh thiếu sáng thực tế, nơi các dạng suy giảm chất lượng chắc chắn sẽ phát sinh do thiết lập chụp ISO cao và phơi sáng lâu, cũng như qua tiến trình thắp sáng (light-up process). Để mô hình hóa các suy giảm này, họ đưa vào các số hạng nhiễu loạn (perturbation terms) cho R và L, đồng thời viết lại Công thức (2) thành:

<<<MATH_TOKEN_0022>>>

$$= R \odot L + R \odot \hat{L} + \hat{R} \odot (L + \hat{L}). \quad (3)$$

<<<MATH_TOKEN_0023>>> và <<<MATH_TOKEN_0024>>> là các đại lượng nhiễu loạn. Để thắp sáng <<<MATH_TOKEN_0025>>>, họ nhân cả hai vế của Công thức (3) với một bản đồ thắp sáng (light-up map) <<<MATH_TOKEN_0026>>> sao cho <<<MATH_TOKEN_0027>>> như sau:

<<<MATH_TOKEN_0028>>>

Sau đó, họ đơn giản hóa Công thức (4) thành:
$$I_{lu} = I \odot \bar{L} = R + C, \quad (5)$$

trong đó <<<MATH_TOKEN_0029>>> biểu thị hình ảnh đã được thắp sáng và <<<MATH_TOKEN_0030>>> <<<MATH_TOKEN_0031>>> chỉ ra <<<MATH_TOKEN_0032>>>. Hệ quả là họ xây dựng khung ORF (One-stage Retinex-based Framework) của mình như sau:

<<<MATH_TOKEN_0033>>>

trong đó <<<MATH_TOKEN_0034>>> biểu thị bộ ước lượng chiếu sáng (illumination estimator) và <<<MATH_TOKEN_0035>>> biểu diễn bộ phục hồi suy giảm (corruption restorer). <<<MATH_TOKEN_0036>>> nhận <<<MATH_TOKEN_0037>>> cùng bản đồ tiên nghiệm chiếu sáng (illumination prior map) <<<MATH_TOKEN_0038>>> làm đầu vào. <<<MATH_TOKEN_0039>>> trong đó $\text{mean}_c$ tính toán các giá trị pixel trung bình qua các kênh. <<<MATH_TOKEN_0040>>> xuất ra ảnh đã thắp sáng <<<MATH_TOKEN_0041>>> và đặc trưng thắp sáng $F_{lu} \in \mathbb{R}^{H \times W \times C}$. Sau đó, $I_{lu}$ và $F_{lu}$ được đưa vào R để phục hồi các suy giảm và tạo ra hình ảnh tăng cường <<<MATH_TOKEN_0042>>>.

**Bộ Ước lượng Chiếu sáng (Illumination Estimator):** <<<MATH_TOKEN_0043>>> Kiến trúc của <<<MATH_TOKEN_0044>>> được thể hiện trong Hình 2 (a) (i). Đầu tiên, E sử dụng một lớp conv1×1 (tích chập với kích thước nhân <<<MATH_TOKEN_0045>>> 1) để kết hợp sự ghép nối (concatenation) của <<<MATH_TOKEN_0046>>> và <<<MATH_TOKEN_0047>>>. Các vùng đủ sáng có thể cung cấp thông tin ngữ cảnh ngữ nghĩa (semantic contextual information) cho các vùng thiếu sáng. Do đó, một tích chập tách biệt theo chiều sâu conv9×9 (depth-wise separable convolution) được áp dụng để mô hình hóa tương tác giữa các vùng có điều kiện ánh sáng khác nhau nhằm tạo ra đặc trưng thắp sáng <<<MATH_TOKEN_0048>>>. Tiếp theo, <<<MATH_TOKEN_0049>>> sử dụng một <<<MATH_TOKEN_0050>>> để tổng hợp <<<MATH_TOKEN_0051>>> nhằm tạo ra bản đồ thắp sáng <<<MATH_TOKEN_0052>>>, vốn được dùng để thắp sáng I trong Công thức (4).

**Transformer Được Dẫn đường bởi Chiếu sáng (Illumination-Guided Transformer - IGT):** Như được minh họa trong Hình 2 (a) (ii), IGT áp dụng kiến trúc dạng chữ U (U-shaped architecture) ba tỷ lệ [10, 13–16]. Đầu vào của IGT là hình ảnh đã được thắp sáng $I_{lu}$. Trong nhánh lấy mẫu xuống (downsampling branch), <<<MATH_TOKEN_0053>>> trải qua một <<<MATH_TOKEN_0054>>>, một IGAB, một tích chập có bước nhảy strided conv4×4, hai IGAB và một strided conv4×4 để tạo ra các đặc trưng phân cấp <<<MATH_TOKEN_0055>>> với <<<MATH_TOKEN_0056>>> = 0, 1, 2. Sau đó, $F_2$ đi qua hai IGAB. Tiếp theo, một cấu trúc đối xứng được thiết kế làm nhánh lấy mẫu lên (upsampling branch). Các kết nối tắt (skip connections) được sử dụng để giảm thiểu sự mất mát thông tin do nhánh lấy mẫu xuống gây ra. Nhánh lấy mẫu lên xuất ra hình ảnh phần dư $I_{re} \in$ <<<MATH_TOKEN_0057>>>. Sau đó, hình ảnh tăng cường <<<MATH_TOKEN_0058>>> được rút ra từ tổng của <<<MATH_TOKEN_0059>>> và <<<MATH_TOKEN_0060>>>.

Hình 2. Tổng quan về Retinexformer [8]. (a) Retinexformer áp dụng khung ORF đề xuất bao gồm bộ ước lượng chiếu sáng (i) và bộ phục hồi suy giảm (ii) IGT. (b) Đơn vị cơ bản của IGT là IGAB, bao gồm hai chuẩn hóa tầng (layer normalization - LN), một IG-MSA và một mạng truyền thẳng (feed-forward network - FFN). (c) IG-MSA sử dụng các biểu diễn chiếu sáng thu được bởi ORF để điều hướng tính toán của cơ chế tự chú ý (self-attention).

**IG-MSA:** Như được minh họa trong Hình 2 (c), đặc trưng thắp sáng <<<MATH_TOKEN_0061>>> được ước lượng bởi <<<MATH_TOKEN_0062>>> được đưa vào từng IG-MSA của IGT. Đầu tiên, đặc trưng đầu vào được định hình lại thành các token <<<MATH_TOKEN_0063>>> <<<MATH_TOKEN_0064>>> và chia thành <<<MATH_TOKEN_0065>>> đầu (heads):

<<<MATH_TOKEN_0066>>>

trong đó <<<MATH_TOKEN_0067>>> và <<<MATH_TOKEN_0068>>>. Sau đó <<<MATH_TOKEN_0069>>> được chiếu tuyến tính thành <<<MATH_TOKEN_0070>>> và <<<MATH_TOKEN_0071>>>:

<<<MATH_TOKEN_0072>>>

trong đó <<<MATH_TOKEN_0073>>> và <<<MATH_TOKEN_0074>>> là các tham số có thể học được và $T$ biểu thị phép chuyển vị ma trận. Tiếp theo, họ sử dụng đặc trưng thắp sáng <<<MATH_TOKEN_0075>>> mã hóa thông tin chiếu sáng và sự tương tác của các vùng có điều kiện ánh sáng khác nhau để điều hướng quá trình tính toán tự chú ý (self-attention). Họ định hình lại <<<MATH_TOKEN_0076>>> thành <<<MATH_TOKEN_0077>>> và chia nó thành <<<MATH_TOKEN_0078>>> đầu:

<<<MATH_TOKEN_0079>>>

trong đó <<<MATH_TOKEN_0080>>>. Sau đó, cơ chế tự chú ý được xây dựng theo công thức:

một mã hóa vị trí có thể học được (learnable positional encoding) <<<MATH_TOKEN_0081>>> để tạo ra các token đầu ra <<<MATH_TOKEN_0082>>>. Cuối cùng, họ định hình lại <<<MATH_TOKEN_0083>>> để thu được đặc trưng đầu ra <<<MATH_TOKEN_0084>>>,

trong đó <<<MATH_TOKEN_0085>>> là tham số có thể học được. <<<MATH_TOKEN_0086>>> Sau đó, <<<MATH_TOKEN_0087>>> đầu được nối lại để đi qua một tầng <<<MATH_TOKEN_0088>>> và cộng thêm.

Bên cạnh Retinexformer [8], đội thi cũng áp dụng giải pháp chiến thắng MST [11, 12] của họ tại Thử thách Phục hồi Quang phổ NTIRE 2022 <<<MATH_TOKEN_0089>>> như một phương pháp phụ trợ để kết hợp mô hình (ensemble). Mã nguồn được phát hành tại https://github.com/caiyuanhao1998/MST và https://github.com/caiyuanhao1998/MST-plus-plus.
