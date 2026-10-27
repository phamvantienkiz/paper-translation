<<<MATH_TOKEN_0206>>>

<<<MATH_TOKEN_0207>>>

<<<MATH_TOKEN_0208>>>

Cách tiếp cận này cho phép giải pháp chỉ sở hữu 387.414 tham số trong khi vẫn đạt được hiệu suất có tính cạnh tranh cao. Nó có thể xử lý hình ảnh 1024x1024 chỉ trong 0,14 giây và hình ảnh 512x512 trong 0,04 giây. Tốc độ nhanh kết hợp với độ phức tạp thấp khiến nó phù hợp cho các ứng dụng thực tế khác nhau, nơi mà sự cân bằng giữa hiệu suất và tốc độ là rất quan trọng.

**Cài đặt thực nghiệm (ataza):** Giải pháp, được phát triển bằng Python với khung PyTorch, đã được huấn luyện trên CPU Intel i7-8700 <<<MATH_TOKEN_0209>>> 3,20 GHz, RAM 16 GB và card đồ họa NVIDIA GeForce RTX 3070. Dữ liệu do cuộc thi cung cấp được sử dụng độc quyền để huấn luyện mô hình. Bộ dữ liệu huấn luyện bao gồm 230 cặp hình ảnh, mỗi hình ảnh có kích thước 2992x2000 pixel. Trong số này, 220 hình ảnh được phân bổ cho việc huấn luyện, 10 hình ảnh còn lại được dành riêng để xác thực. Để tăng cường tập dữ liệu, các mảnh không chồng lấn có kích thước 256x256 pixel đã được trích xuất từ mỗi hình ảnh và được sử dụng để huấn luyện mô hình. Quá trình huấn luyện kéo dài 70 epoch, áp dụng chiến lược Giảm dần Cosine (Cosine Annealing) với độ dài chu kỳ là 10 epoch và tốc độ học ban đầu được đặt ở mức 0,0005. Để huấn luyện mô hình, bộ tối ưu hóa Adam kết hợp với tính năng độ chính xác hỗn hợp của PyTorch đã được sử dụng và kích thước batch được đặt là 8.

### 4.16. KLETech-CEVI.LowlightHypnotise

Hình 16. Tổng quan về Multi-scale Feature FusionNet (MFNN) được đề xuất. Bộ mã hóa trích xuất các đặc trưng ở ba tỷ lệ riêng biệt, với thông tin được truyền qua các phân cấp (hộp nét đứt màu xanh lá cây). Thông tin không gian và ngữ cảnh toàn cục - cục bộ mịn được học thông qua Khối GLSC (hộp nét đứt màu cam). Tại bộ giải mã, sự trao đổi thông tin diễn ra theo các phân cấp ngược lại (hộp nét đứt màu xanh lam).

**Mô tả:** Khung MFNN đề xuất bao gồm ba mô-đun chính: bộ mã hóa đặc trưng không gian - ngữ cảnh phân cấp (hierarchical spatio-contextual - HSC), khối Không gian - Ngữ cảnh Toàn cục - Cục bộ (Global-Local Spatio-Contextual - GLSC), và bộ giải mã không gian - ngữ cảnh phân cấp (HSC), như được thể hiện trong Hình 16. Thông thường, các mạng tăng cường ảnh thiếu sáng sử dụng việc co giãn đặc trưng để thay đổi kích thước của các trường tiếp nhận (receptive fields). Các trường tiếp nhận biến đổi tạo điều kiện thuận lợi cho việc học các biến sai từ cục bộ đến toàn cục trong các đặc trưng. Với động lực này, chúng tôi học thông tin ngữ cảnh từ các đặc trưng đa tỷ lệ trong khi vẫn bảo tồn các chi tiết không gian độ phân giải cao. Chúng tôi đạt được điều này thông qua một mạng mã hóa - giải mã kiểu phân cấp với các khối phần dư làm xương sống cho việc học. Cho một hình ảnh đầu vào x, bộ mã hóa phân cấp đa tỷ lệ đề xuất sẽ trích xuất các đặc trưng nông ở ba tỷ lệ riêng biệt và được biểu diễn như sau:

(18)

trong đó <<<MATH_TOKEN_0210>>> là các đặc trưng <<<MATH_TOKEN_0211>>> <<<MATH_TOKEN_0212>>> tỷ lệ <<<MATH_TOKEN_0213>>> từ không gian được lấy mẫu của hình ảnh đầu vào <<<MATH_TOKEN_0214>>> và <<<MATH_TOKEN_0215>>> đại diện cho bộ mã hóa phân cấp ở tỷ lệ s. Để học các biểu diễn từ toàn cục đến cục bộ từ các đặc trưng mức nông này, chúng tôi đề xuất khối Không gian - Ngữ cảnh Toàn cục - Cục bộ (GLSC), với các khối phần dư làm mạng xương sống. Các đặc trưng sâu đã học được biểu diễn như sau:

<<<MATH_TOKEN_0216>>>

trong đó <<<MATH_TOKEN_0217>>> là đặc trưng sâu ở tỷ lệ <<<MATH_TOKEN_0218>>>, <<<MATH_TOKEN_0219>>> là các đặc trưng nông được trích xuất ở tỷ lệ <<<MATH_TOKEN_0220>>> và <<<MATH_TOKEN_0221>>> đại diện cho các khối phần dư ở các tỷ lệ tương ứng. Chúng tôi giải mã các đặc trưng sâu thu được ở các tỷ lệ khác nhau bằng bộ giải mã phân cấp được đề xuất và được biểu diễn bởi:

<<<MATH_TOKEN_0222>>>

trong đó <<<MATH_TOKEN_0223>>> là đặc trưng đã giải mã ở tỷ lệ <<<MATH_TOKEN_0224>>>, và <<<MATH_TOKEN_0225>>> đại diện cho bộ giải mã phân cấp. Các đặc trưng đã giải mã và các đặc trưng được nâng tỷ lệ ở mỗi thang đo được chuyển đến các tầng tái tạo <<<MATH_TOKEN_0226>>> để thu được hình ảnh tăng cường <<<MATH_TOKEN_0227>>>. Các đặc trưng nâng tỷ lệ từ mỗi thang đo được xếp chồng lên nhau và biểu diễn như sau:

<<<MATH_TOKEN_0228>>>

(21)

trong đó <<<MATH_TOKEN_0229>>> và <<<MATH_TOKEN_0230>>> là các đặc trưng đã giải mã ở ba tỷ lệ riêng biệt, <<<MATH_TOKEN_0231>>> đại diện cho tập hợp các đặc trưng cuối cùng được chuyển đến các tầng tái tạo để thu được hình ảnh tăng cường $\hat{y}$:

$$\hat{y} = \mathcal{M}(P), \quad (22)$$

trong đó <<<MATH_TOKEN_0232>>> là hình ảnh tăng cường thu được từ các tầng tái tạo $\mathcal{M}$. Chúng tôi tối ưu hóa việc học của MFNN bằng hàm mất mát đề xuất <<<MATH_TOKEN_0233>>> và được xác định như sau:

<<<MATH_TOKEN_0234>>>

trong đó <<<MATH_TOKEN_0235>>> và <<<MATH_TOKEN_0236>>> là các trọng số. Qua thực nghiệm chúng tôi đặt các trọng số thành <<<MATH_TOKEN_0237>>> và <<<MATH_TOKEN_0238>>> là sự kết hợp có trọng số của ba hàm mất mát riêng biệt lấy cảm hứng từ [25–27, 36]: mất mát <<<MATH_TOKEN_0239>>> để giảm thiểu sai số ở cấp độ pixel, mất mát cảm nhận [43] để khôi phục hiệu quả thông tin ngữ cảnh giữa ảnh dữ liệu chuẩn thực tế và ảnh đầu ra, mất mát độ không tương đồng cấu trúc đa tỷ lệ để khôi phục các chi tiết cấu trúc. Mục tiêu ở đây là giảm thiểu mất mát kết hợp có trọng số <<<MATH_TOKEN_0240>>> được xác định như sau:

trong đó <<<MATH_TOKEN_0241>>> biểu thị các tham số có thể học được của khung đề xuất, <<<MATH_TOKEN_0242>>> là tổng số cặp huấn luyện, <<<MATH_TOKEN_0243>>> và <<<MATH_TOKEN_0244>>> lần lượt là hình ảnh đầu vào và đầu ra, và <<<MATH_TOKEN_0245>>> là khung đề xuất cho bài toán tăng cường ảnh thiếu sáng.

**Cài đặt thực nghiệm (MFNN):** Chúng tôi huấn luyện MFNN đề xuất bằng Python (v3.8) kết hợp với khung PyTorch và tiến hành các thử nghiệm trên 2 GPU NVIDIA RTX 3090 cùng với CPU AMD Ryzen ThreadRipper 3960X. Chúng tôi sử dụng 16 khối phần dư được chia thành ba tầng phân cấp và tạo ra 256 bản đồ đặc trưng cho mỗi tỷ lệ. Chúng tôi huấn luyện MFNN đề xuất trên tập dữ liệu được cung cấp trong thử thách cùng với Bộ dữ liệu LOL [71] với các mảnh có kích thước 600*400. Trong quá trình huấn luyện, chúng tôi sử dụng bộ tối ưu hóa Adam với <<<MATH_TOKEN_0246>>> <<<MATH_TOKEN_0247>>>, đặt tốc độ học <<<MATH_TOKEN_0248>>> và huấn luyện MFNN đề xuất trong 1000 epoch. Chúng tôi tối ưu hóa quá trình học với <<<MATH_TOKEN_0249>>> đề xuất. Trong quá trình kiểm thử, chúng tôi sử dụng hình ảnh có độ phân giải đầy đủ (2992 <<<MATH_TOKEN_0250>>> 2000) trên một GPU RTX 3090 đơn lẻ. Thời gian kiểm thử trung bình cho một ảnh ở độ phân giải đầy đủ là 0,53 giây trên GPU RTX 3090.

### 4.17. 221B

Hình 17. Tổng quan về quá trình huấn luyện mô hình khuếch tán với hàm mất mát entropy không gian khả vi do đội 221B đề xuất.

*Ban tổ chức muốn nhấn mạnh rằng phương pháp này đã giành vị trí quán quân trên bảng xếp hạng LPIPS, với số điểm 0,1084, vượt trội hơn cả công trình đứng đầu chung cuộc (với điểm 0,1221).*

**Mô tả:** Hầu hết các công trình dựa trên mô hình khuếch tán hiện nay [37] chỉ đơn thuần sử dụng hàm mất mát <<<MATH_TOKEN_0251>>> để huấn luyện mạng dự đoán nhiễu theo cách xác định (deterministic), vốn luôn tạo ra các nhiễu trung gian (hoặc trạng thái trung gian) trơn nhẵn trong quá trình nghịch đảo. Mặc dù chất lượng cảm nhận có thể được cải thiện với các bước khuếch tán dài hơn, nhưng việc khám phá một hàm mất mát dựa trên cảm nhận để hỗ trợ quá trình huấn luyện là hoàn toàn hợp lý. Trong công trình này, họ đề xuất học mạng từ góc nhìn thống kê thuần túy, tức là học trực tiếp các phân phối thay vì khoảng cách từng pixel. Ý tưởng cốt lõi là entropy không gian khả vi (differentiable spatial entropy) được rút ra từ ước lượng mật độ nhân (Kernel Density Estimation - KDE) và đo lường thông tin không gian của một hình ảnh. Một cách hình thức, theo [3, 63], KDE hai chiều được định nghĩa là xác suất của một giá trị cường độ cụ thể <<<MATH_TOKEN_0252>>> và vùng lân cận của nó <<<MATH_TOKEN_0253>>> như sau:

<<<MATH_TOKEN_0254>>>
<<<MATH_TOKEN_0255>>>

<<<MATH_TOKEN_0256>>>

trong đó <<<MATH_TOKEN_0257>>> và <<<MATH_TOKEN_0258>>> là các hàm nhân tùy ý (chúng cũng có thể giống nhau). Để tận dụng KDE không gian khả vi trong quá trình tạo ảnh, công trình này xem xét việc đưa vào relative entropy (còn gọi là độ phân kỳ KL - KL-divergence) để đo khoảng cách phân phối giữa ảnh dự đoán và dữ liệu chuẩn thực tế (ground truth). Với <<<MATH_TOKEN_0259>>> và <<<MATH_TOKEN_0260>>> lần lượt đại diện cho các phân phối xác suất của dữ liệu chuẩn và dự đoán được tính toán từ Công thức (25), relative entropy không gian được định nghĩa là:

<<<MATH_TOKEN_0261>>>

Mô hình khuếch tán của họ được xây dựng trên phương trình vi phân ngẫu nhiên hoàn nguyên trung bình (mean-reverting SDE) [53, 54]. Bằng cách tối ưu hóa khoảng cách phân phối dựa trên entropy giữa các dự đoán và các trạng thái chuẩn thực tế, kết quả của họ có chất lượng thị giác tốt hơn so với kết quả chỉ sử dụng hàm mất mát <<<MATH_TOKEN_0262>>>. Hình 17 minh họa tổng quan về quá trình huấn luyện khuếch tán được đề xuất.

**Cài đặt thực nghiệm (221B):** Đội này sử dụng tập dữ liệu thiếu sáng được cung cấp nhưng tách riêng 10 cặp ảnh để xác thực. Khung Refusion được sử dụng làm đường cơ sở và đội thi đã trực tiếp thay đổi hàm mất mát của nó thành entropy không gian khả vi đề xuất. Trong quá trình huấn luyện, tất cả các hình ảnh đều được cắt với kích thước mảnh <<<MATH_TOKEN_0263>>> 128, và tổng số bước lặp huấn luyện được đặt là 500.000 với kích thước batch là 16. Theo Refusion [54], công trình này sử dụng bộ tối ưu hóa AdamW [51] và bộ điều chỉnh 'CosineDecay' với tốc độ học ban đầu là 0,0001. Và các bước khuếch tán được cố định là 100 trong cả huấn luyện và kiểm thử.

### 4.18. KLETech-CEVI_Dark Knights

Hình 18. Khung của Mô-đun Chiếu sáng Tự hiệu chuẩn (Được tái hiện từ [55]). Chúng tôi sử dụng một biến thể của phương pháp này để tăng cường hình ảnh thiếu sáng với hàm mất mát tùy chỉnh.

**Mô tả:** Theo lý thuyết Retinex, tồn tại một mối quan hệ giữa hình ảnh thiếu sáng quan sát được, ký hiệu là $y$, và hình ảnh rõ nét mong muốn $z$, được biểu diễn dưới dạng:
