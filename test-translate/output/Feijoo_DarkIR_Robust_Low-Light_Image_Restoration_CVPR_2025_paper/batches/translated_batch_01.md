# DarkIR: Phục hồi hình ảnh thiếu sáng mạnh mẽ (DarkIR: Robust Low-Light Image Restoration)

**Daniel Feijoo** $^{1\dagger}$, **Juan C. Benito** $^1$, **Alvaro Garcia** $^1$, **Marcos V. Conde** $^{1,2\dagger}$  
$^1$ Cidaut AI, Valladolid, Tây Ban Nha  
$^2$ Computer Vision Lab, Đại học Würzburg, Đức  
Mã nguồn: https://github.com/cidautai/DarkIR | $^\dagger$ Tác giả liên hệ: {danfei, marcos.conde@cidaut.es}

![Hình 1. Các phương pháp Tăng cường hình ảnh thiếu sáng (LLIE) và phục hồi trước đây không mạnh mẽ trước hiện tượng mờ nhòe và biến đổi độ sáng. Mô hình đa nhiệm của chúng tôi có khả năng phục hồi ảnh thiếu sáng thực tế dưới các điều kiện độ rọi, nhiễu và độ mờ biến thiên. Phóng to để xem chi tiết.](figures/figure_01.png)

Hình 1. Các phương pháp Tăng cường hình ảnh thiếu sáng (LLIE) và phục hồi trước đây không mạnh mẽ trước hiện tượng mờ nhòe và biến đổi độ sáng. Mô hình đa nhiệm của chúng tôi có khả năng phục hồi ảnh thiếu sáng thực tế dưới các điều kiện độ rọi, nhiễu và độ mờ biến thiên. Phóng to để xem chi tiết.

### Tóm tắt (Abstract)

Nhiếp ảnh ban đêm hoặc trong điều kiện tối tăm thường chịu ảnh hưởng đồng thời bởi nhiễu, thiếu sáng và hiện tượng nhòe mờ do môi trường ánh sáng yếu và việc thường xuyên phải dùng thời gian phơi sáng dài. Mặc dù Khử mờ (Deblurring) và Tăng cường hình ảnh thiếu sáng (Low-Light Image Enhancement - LLIE) có mối liên hệ mật thiết trong những điều kiện này, hầu hết các hướng tiếp cận phục hồi hình ảnh hiện nay đều giải quyết các bài toán này một cách riêng biệt. Trong bài báo này, chúng tôi đề xuất một mạng nơ-ron hiệu quả và mạnh mẽ cho tác vụ phục hồi hình ảnh thiếu sáng đa nhiệm. Thay vì đi theo xu hướng hiện nay của các mô hình dựa trên Transformer, chúng tôi đề xuất các cơ chế chú ý (attention mechanism) mới nhằm mở rộng trường tiếp nhận (receptive field) của các mạng CNN hiệu năng cao. Phương pháp của chúng tôi cắt giảm đáng kể chi phí tính toán xét về tham số và số phép toán MAC so với các phương pháp trước đây. Mô hình của chúng tôi, **DarkIR**, đạt được các kết quả hiện đại nhất (SOTA) mới trên các bộ tiêu chuẩn đánh giá (benchmark) phổ biến gồm LOLBlur, LOLv2 và Real-LOLBlur, đồng thời có khả năng tổng quát hóa xuất sắc trên ảnh chụp đêm và vùng tối trong thế giới thực.

---

### 1. Giới thiệu (1. Introduction)

Trong điều kiện ban đêm hoặc ánh sáng yếu, chúng ta có thể mô hình hóa quá trình hình thành hình ảnh như sau:

<<<MATH_TOKEN_0002>>>

trong đó $\mathbf{y}$ là hình ảnh tối quan sát được, $\mathbf{x}$ là khung cảnh chụp gốc không bị suy giảm, $\mathbf{k}$ biểu thị kernel làm mờ (hàm phân tán điểm - point-spread function hay PSF) của ống kính, $\mathbf{n}$ là nhiễu cảm biến cộng tính, và <<<MATH_TOKEN_0003>>> là một hàm điều khiển dải động và độ bão hòa điểm ảnh. Chúng tôi sử dụng <<<MATH_TOKEN_0004>>> để biểu diễn toán tử tích chập.

So với điều kiện ban ngày, trong điều kiện ánh sáng yếu, độ nhiễu (bao gồm nhiễu hạt photon và nhiễu đọc cảm biến) cao hơn đáng kể. Khi chụp ảnh ban đêm, máy ảnh thường sử dụng thời gian phơi sáng dài (tốc độ màn trập chậm) để cho phép nhiều ánh sáng khả dụng đi vào cảm biến hơn. Tuy nhiên, thời gian phơi sáng dài dễ dẫn đến hiện tượng bóng ma (ghosting) và các hiệu ứng giả nhòe mờ (blurring artifacts). Những suy giảm chất lượng này càng trở nên nghiêm trọng trên điện thoại thông minh do khẩu độ cố định và hệ thống quang học giới hạn. Vì những lý do này, việc kết hợp đồng thời tăng cường hình ảnh thiếu sáng và khử mờ là yếu tố sống còn cho nhiếp ảnh điện toán di động [12, 65] — xem các mẫu minh họa tại Hình 1.

Trong mọi hoàn cảnh thực tế, hình ảnh thu được đều biểu hiện những mức độ nhiễu và nhòe mờ nhất định [13]. Bằng cách sử dụng chân máy (tripod) để cố định góc chụp, chúng ta có thể giảm đáng kể độ mờ. Hơn nữa, nếu có hệ thống chiếu sáng thích hợp, độ nhiễu cũng có thể được triệt tiêu [1, 20].

Tuy nhiên, ngày nay phần lớn các bức ảnh đều được chụp bằng điện thoại thông minh cầm tay. Do kích thước cảm biến và hệ quang học hạn chế, các thiết bị này sử dụng các Bộ xử lý tín hiệu hình ảnh (ISP) phức tạp hơn [10, 12] so với máy ảnh không gương lật ống kính đơn kỹ thuật số (DSLM). Nhiếp ảnh di động hiện vẫn còn khoảng cách so với các tiêu chuẩn chất lượng của DSLM; tuy nhiên, các nghiên cứu gần đây trong lĩnh vực thị giác máy tính mức thấp (low-level computer vision) và nhiếp ảnh điện toán đang từng bước thu hẹp khoảng cách này. Tăng cường hình ảnh thiếu sáng (LLIE) [3, 14, 30, 31, 45, 64], khử mờ hình ảnh [21, 25, 38, 40] và nâng cao chất lượng ảnh chụp đêm [42, 65] là những bài toán nghiên cứu đang rất được quan tâm.

Chẳng hạn, việc ngăn chặn độ mờ do rung tay khi chụp đã được nghiên cứu sâu rộng, ngay cả trong môi trường thiếu sáng [29, 62]. Tuy nhiên, trong phần lớn trường hợp, các bài toán này vẫn được xử lý riêng biệt; vì vậy, các phương pháp khử mờ hiện đại nhất (SOTA) không tổng quát hóa tốt cho ảnh ban đêm, và các phương pháp tăng cường thiếu sáng tốt nhất lại không thể triệt tiêu độ mờ rõ rệt. Đây là một hạn chế lớn, bởi người dùng buộc phải tinh chỉnh (fine-tuning), lưu trữ và ghép nối tuần tự nhiều mô hình chuyên biệt, từ đó gây cản trở việc triển khai thực tế.

Theo hiểu biết của chúng tôi, rất ít công trình hướng tới việc giải quyết đồng thời các tác vụ này (khử nhiễu, khử mờ và LLIE) theo phương thức đầu-cuối kết hợp (joint end-to-end) [6, 33, 63, 65], trong đó LEDNet [65] là công trình nổi bật nhất. Chúng tôi theo đuổi hướng nghiên cứu này vì việc khai thác mối tương quan giữa các dạng suy giảm chất lượng cho phép đạt hiệu năng cao nhất về khả năng tái tạo hình ảnh, tính ứng dụng và hiệu quả vận hành.

**Đóng góp của chúng tôi:** Chúng tôi đề xuất một mạng nơ-ron tích chập (CNN) hoạt động đồng thời trên cả miền không gian và miền tần số. Trong miền không gian, chúng tôi tập trung triệt tiêu nhiễu $\mathbf{n}$ và độ mờ không đồng nhất $\mathbf{k}$ thông qua cơ chế chú ý không gian có trường tiếp nhận lớn (large receptive field spatial attention). Mặt khác, trong miền Fourier, chúng tôi có thể cải thiện điều kiện thiếu sáng một cách dễ dàng [28, 44] nhờ bản chất toàn cục của bài toán. Các đóng góp chính gồm:

1. Thiết kế mạng nơ-ron gọn nhẹ với cơ chế chú ý tần số và cơ chế chú ý trường tiếp nhận lớn, kết hợp hài hòa thông tin không gian và tần số.
2. Mô hình **DarkIR** đạt kết quả hiện đại nhất (SOTA) trên các bộ tiêu chuẩn đánh giá (benchmark) phổ biến LOLBlur và Real-LOLBlur [65], tăng hơn +1dB PSNR so với LEDNet [65], đồng thời giảm bớt chi phí tính toán.
3. DarkIR thiết lập một mô hình cơ sở (baseline) mới cho tác vụ nâng cao chất lượng ảnh đêm/tối đa nhiệm.

---

### 2. Các công trình liên quan (2. Related Work)

**Khử mờ hình ảnh (Image Deblurring):** Đã có hàng thập kỷ nghiên cứu về việc tái tạo những khung cảnh sắc nét. Quá trình khử mờ ảnh được chia thành các phương pháp không mù (non-blind) và phương pháp mù (blind). Trong khi các phương pháp non-blind dựa vào kernel làm mờ $\mathbf{k}$ (hoặc hàm phân tán điểm PSF) đã biết để xử lý, thì các phương pháp blind không có bất kỳ thông tin tiên nghiệm nào về dạng suy giảm làm mờ.

Những năm gần đây, nhiều giải pháp dựa trên học sâu đã được đề xuất cho cả khử mờ blind và non-blind [25, 38], vượt trội so với các phương pháp truyền thống ở cả hai kịch bản. Các phương pháp tiếp cận non-blind đem lại giải pháp ưu việt khi chỉ yêu cầu các cặp ảnh mờ-nét để huấn luyện mô hình mà không cần ước lượng PSF hay cấu hình cảm biến. Hầu hết các cách tiếp cận này đều độc lập với cảm biến (sensor-agnostic), nghĩa là chúng có thể xử lý tốt hình ảnh sRGB thu nhận từ nhiều loại máy ảnh khác nhau.

Hiện nay, phần lớn các phương pháp này được xây dựng trên nền tảng mạng nơ-ron tích chập (CNN) [4, 25, 37, 57]. Trong DeblurGAN [25], các tác giả ứng dụng Mạng đối nghịch tạo sinh (GAN) để giải quyết vấn đề. Gần đây hơn, nhóm tác giả trong [24] đã triển khai một mô hình Transformer dựa trên miền tần số hiệu quả cho bài toán khử mờ. Ngoài ra còn có các phương pháp tối ưu hóa lặp và mô hình khuếch tán (diffusion models) [33, 49].

**Tăng cường hình ảnh thiếu sáng (Low-Light Image Enhancement - LLIE):** Các phương pháp sơ khởi thường dựa trên đặc tính thống kê ảnh hoặc thông tin tiên nghiệm [2, 18], phần lớn dựa trên Thuyết Retinex kinh điển [26].

Theo đà phát triển của học sâu, các phương pháp LLIE hiện đại chủ yếu dựa trên Mạng nơ-ron tích chập (CNN) như RetinexNet [48] (cùng tập dữ liệu LOL đi kèm), ZeroDCE [16] và SCI [35]. Những nghiên cứu mới nhất tiếp tục khai phá năng lực của Transformer trong tác vụ này, điển hình là RetinexFormer [3], hoặc tận dụng thông tin miền tần số Fourier để tăng cường biên độ ảnh, tiêu biểu là FourLLIE [44].

**Khử mờ và tăng cường trong điều kiện thiếu sáng (Low-Light Blur Enhancement):** Mặc dù khử mờ và tăng cường thiếu sáng là hai bài toán thu hút nhiều sự quan tâm, việc giải quyết đồng thời cả hai lại là một thách thức lớn và có rất ít công trình nghiên cứu trực diện [6, 33, 63, 65]. NBDN [6] đề xuất một mạng non-blind nhằm nâng cao chất lượng ảnh đêm bị bão hòa sáng. Khi giải tích chập ảnh để phục hồi độ sắc nét, thuật toán phải xử lý đồng thời cả nhiễu lẫn các vùng bão hòa. Nhóm tác giả đã chỉ ra rằng các phương pháp trước đó đều gặp khó khăn lớn trước bài toán hỗn hợp này.

Mặt khác, với LEDNet [65], các tác giả tìm cách giải bài toán tăng cường thiếu sáng khi giả định hình ảnh cũng bị nhòe mờ. Đây là một giả định rất sát thực tế do smartphone bắt buộc phải kéo dài thời gian phơi sáng trong bóng tối. Họ đã phát triển một kiến trúc mã hóa - giải mã (encoder-decoder) và giới thiệu hai bộ dữ liệu chuẩn phổ biến LOLBlur và Real-LOLBlur.

---

### 3. Phương pháp đề xuất (3. Method)

![Hình 2. Sơ đồ tổng quan của DarkIR. Mạng nơ-ron tuân theo kiến trúc bộ mã hóa - giải mã (encoder-decoder). Chúng tôi sử dụng các khối khác nhau cho quá trình mã hóa và giải mã theo cấu trúc Metaformer [56]. Bộ mã hóa tập trung vào các vấn đề chiếu sáng trong điều kiện ánh sáng yếu bằng cách sử dụng thông tin Fourier. Nhờ đó, bộ mã hóa tạo ra một hình ảnh tái tạo độ phân giải thấp ˆx↓8 với độ sáng đã được hiệu chỉnh. Bộ giải mã tập trung vào việc nâng độ phân giải (upscaling) và giảm độ mờ bằng cách sử dụng các đặc trưng đã được mã hóa tăng cường ánh sáng trước đó. Để đạt được điều này, bộ giải mã sử dụng cơ chế chú ý không gian có trường tiếp nhận lớn (large receptive field spatial attention). Thiết kế này cho phép mô hình gọn nhẹ của chúng tôi có ít tham số và FLOPs hơn so với các phương pháp trước đây.](figures/figure_02.png)

Hình 2. Sơ đồ tổng quan của DarkIR. Mạng nơ-ron tuân theo kiến trúc bộ mã hóa - giải mã (encoder-decoder). Chúng tôi sử dụng các khối khác nhau cho quá trình mã hóa và giải mã theo cấu trúc Metaformer [56]. Bộ mã hóa tập trung vào các vấn đề chiếu sáng trong điều kiện ánh sáng yếu bằng cách sử dụng thông tin Fourier. Nhờ đó, bộ mã hóa tạo ra một hình ảnh tái tạo độ phân giải thấp $\hat{x}_{\downarrow 8}$ với độ sáng đã được hiệu chỉnh. Bộ giải mã tập trung vào việc nâng độ phân giải (upscaling) và giảm độ mờ bằng cách sử dụng các đặc trưng đã được mã hóa tăng cường ánh sáng trước đó. Để đạt được điều này, bộ giải mã sử dụng cơ chế chú ý không gian có trường tiếp nhận lớn (large receptive field spatial attention). Thiết kế này cho phép mô hình gọn nhẹ của chúng tôi có ít tham số và FLOPs hơn so với các phương pháp trước đây.

Chúng tôi kế thừa triết lý Metaformer [56] để thiết kế mạng nơ-ron. Cấu trúc này tối giản hóa các kiến trúc Transformer thành các khối cơ bản gồm hai thành phần: cơ chế chú ý toàn cục (ví dụ: bộ trộn token - token mixer) và mạng truyền thẳng (feed-forward network - FFN, MLP). Dạng công thức chuẩn của các khối này là:

<<<MATH_TOKEN_0006>>>

<<<MATH_TOKEN_0007>>>

trong đó <<<MATH_TOKEN_0009>>> là các đặc trưng đầu vào và <<<MATH_TOKEN_0010>>> là các đặc trưng đầu ra của khối. Hầu hết các mô hình phục hồi hình ảnh phổ biến, ví dụ như NAFNet [7], đều áp dụng cấu trúc này và tinh chỉnh mô-đun chú ý (Attention module) cho phù hợp với từng tác vụ.

Chúng tôi phát triển cấu trúc Metaformer bằng cách xây dựng các khối chuyên biệt riêng cho LLIE và khử mờ. Ngoài ra, chúng tôi sử dụng cơ chế cổng đơn giản (simple gates - SG) và cơ chế chú ý kênh đơn giản hóa (simplified channel attention - SCA) thay thế cho các hàm kích hoạt phi tuyến thông thường tương tự [7].

**Tăng cường ánh sáng yếu có thể giải quyết hiệu quả trong miền tần số:**

Nhiều công trình nghiên cứu [28, 44] đã chứng minh rằng các điều kiện chiếu sáng yếu có mối tương quan rất cao với phổ biên độ (amplitude) của hình ảnh trong miền Fourier. Do đó, chỉ bằng cách tăng cường biên độ của hình ảnh (và giữ nguyên pha), chúng ta có thể hiệu chỉnh đáng kể độ sáng của bức ảnh. Hơn nữa, đặc tính này luôn nhất quán trên nhiều thang độ phân giải khác nhau [28]. Do đó, chúng ta có thể ước lượng một hình ảnh đã tăng cường ánh sáng ở độ phân giải thấp rồi nâng kích thước lên.

**Làm sắc nét và giảm nhòe mờ đòi hỏi trường tiếp nhận lớn:**
Yêu cầu này thường đạt được bằng cách trích xuất các đặc trưng tầng sâu song song với việc giảm mẫu hình ảnh — như hướng tiếp cận của NAFNet [7]. Một giải pháp thay thế là sử dụng kernel tích chập kích thước lớn [32], tuy nhiên điều này làm tăng đáng kể độ phức tạp tính toán và dung lượng bộ nhớ.

**Mô hình DarkIR:** Trong Hình 2, chúng tôi trực quan hóa kiến trúc mô hình. Khác với phần lớn các giải pháp trước đây, chúng tôi sử dụng hai khối thiết kế khác nhau cho bộ mã hóa (encoder) và bộ giải mã (decoder). Ý tưởng chủ đạo đằng sau thiết kế bất đối xứng này là thực hiện tăng cường ánh sáng yếu ở độ phân giải thấp ngay trong bộ mã hóa, sau đó khử mờ nhòe trong bộ giải mã, tương tự chiến lược của LEDNet [65]. Bộ giải mã sẽ tiếp nhận các đặc trưng đã được tăng cường ánh sáng từ bộ mã hóa, tập trung toàn lực vào việc nâng mẫu và làm sắc nét bức ảnh tái tạo độ phân giải thấp <<<MATH_TOKEN_0011>>>.

Đối với khối mã hóa nhằm phục hồi điều kiện thiếu sáng, chúng tôi thao tác trong miền Fourier [28, 44]. Đối với khối giải mã, mạng tập trung xử lý trong miền không gian bằng cách tích hợp các phép tích chập giãn nở (dilated convolutions) có trường tiếp nhận lớn. Việc sử dụng các khối chuyên biệt cho từng tác vụ cho phép chúng tôi giảm bớt tổng số lượng khối. Thiết kế này giúp cắt giảm đáng kể số lượng tham số cũng như chi phí tính toán xét về MAC (phép nhân-cộng tích lũy) và FLOPs (phép tính dấu phẩy động mỗi giây).

**Làm sao để đảm bảo Bộ mã hóa đang thực sự tăng cường ánh sáng yếu?** Như mô tả trên Hình 2, các đặc trưng mã hóa được kết hợp tuyến tính thông qua một lớp tích chập để tạo thành một biểu diễn hình ảnh trung gian <<<MATH_TOKEN_0012>>>. Chúng tôi sử dụng biểu diễn này để điều chuẩn mô hình thông qua một hàm mất mát bổ sung. Việc tạo ra một biểu diễn độ phân giải thấp chất lượng tốt đảm bảo rằng phổ biên độ trong miền Fourier đã được tăng cường chính xác.

### 3.1. Bộ mã hóa tăng cường thiếu sáng (Low-light Enhancement Encoder)

Chúng tôi thiết kế các khối mã hóa (**EBlock**) để tăng cường điều kiện chiếu sáng yếu của hình ảnh bằng cách sử dụng thông tin Fourier, tuân thủ cấu trúc Metaformer [56] (và NAFBlock [7]). Khối này gồm hai thành phần: mô-đun chú ý không gian (spatial attention module - **SpAM**) và mạng truyền thẳng trong miền tần số (frequency domain feed-forward network - **FreMLP**).
