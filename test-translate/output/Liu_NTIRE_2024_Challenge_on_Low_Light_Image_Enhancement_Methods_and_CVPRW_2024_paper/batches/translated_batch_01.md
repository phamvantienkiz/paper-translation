# Thử thách NTIRE 2024 về Tăng cường Ảnh Thiếu sáng: Phương pháp và Kết quả

Xiaoning Liu∗, Zongwei Wu∗, Ao Li∗, Florin-Alexandru Vasluianu∗, Yulun Zhang∗, Shuhang Gu∗, Le Zhang∗, Ce Zhu∗, Radu Timofte∗, Zhi Jin, Hongjun Wu, Chenxi Wang, Haitao Ling, Yuanhao Cai, Hao Bian, Yuxin Zheng, Jing Lin, Alan Yuille, Ben Shao, Jin Guo, Tianli Liu, Mohao Wu, Yixu Feng, Shuo Hou, Haotian Lin, Yu Zhu, Peng Wu, Wei Dong, Jinqiu Sun, Yanning Zhang, Qingsen Yan, Wenbin Zou, Weipeng Yang, Yunxiang Li <<<MATH_TOKEN_0001>>>, Qiaomu Wei, Tian Ye, Zhichao Zuo, Sixiang Chen, Zhao Zhang, Suiyi Zhao, Bo Wang, Yan Luo, Mingshen Wang, Junhu Wang, Yanyan Wei, Xiaopeng Sun, Yu Gao, Jiancheng Huang <<<MATH_TOKEN_0002>>> Hongming Chen <<<MATH_TOKEN_0003>>>, Hui Tang, Yuanbin Chen, Yuanbo Zhou, Xinwei Dai, Xintao Qiu, Wei Deng, Qinquan Gao, Tong Tong, Mingjia Li, Jin Hu, Xinyu He, Xiaojie Guo, Sabarinathan, K Uma, A Sasithradevi, B Sathya Bama, S. Mohamed Mansoor Roomi, V.Srivatsav, Jinjuan Wang, Long Sun <<<MATH_TOKEN_0004>>> Qiuying Chen <<<MATH_TOKEN_0005>>> Jiahong Shao, Yizhi Zhang, Marcos V. Conde, Daniel Feijoo, Juan C. Benito, Alvaro García, Jaeho Lee, Seongwan Kim, SharifSMA, Nodirkhuja Khujaev, Roman Tsoy, Ali Murtaza, Uswah Khairuddin, Ahmad ’Athif Mohd Faudzi, Sampada Malagi, Amogh Joshi, Nikhil Akalwadi, Chaitra Desai, Ramesh Ashok Tabib, Uma Mudenagudi, Wenyi Lian, Wenjing Lian, Jagadeesh Kalyanshetti, Vijayalaxmi Ashok Aralikatti, Palani Yashaswini, Nitish Upasi, Dikshit Hegde, Ujwala Patil, Sujata C, Xingzhuo Yan, Wei Hao, Minghan Fu, Pooja choksy, Anjali Sarvaiya, Kishor Upla, Kiran Raja, Hailong Yan <<<MATH_TOKEN_0006>>> Jingyi Zhang, Huan Zheng.

## Tóm tắt (Abstract)

Bài báo này tổng kết Thử thách NTIRE 2024 về Tăng cường Ảnh Thiếu sáng (Low Light Image Enhancement - LLIE), nêu bật các giải pháp và kết quả được đề xuất. Mục tiêu của thử thách này là khám phá thiết kế mạng hoặc giải pháp hiệu quả có khả năng tạo ra các kết quả sáng hơn, rõ ràng hơn và trực quan hấp dẫn khi xử lý nhiều điều kiện khác nhau, bao gồm độ phân giải siêu cao (4K trở lên), chiếu sáng không đồng đều, ngược sáng, tối cực hạn và cảnh đêm. Tổng cộng có 428 người tham gia đã đăng ký thử thách, với 22 đội cuối cùng đã gửi bài hợp lệ. Bài báo này đánh giá tỉ mỉ những tiến bộ hiện đại nhất (SOTA) trong việc tăng cường ảnh thiếu sáng, phản ánh sự tiến bộ đáng kể <<<MATH_TOKEN_0007>>>.

## 1. Giới thiệu (Introduction)

Tăng cường ảnh thiếu sáng (Low light Image enhancement - LLIE), một tác vụ then chốt nhưng đầy thách thức trong thị giác máy tính, nhằm mục đích cải thiện khả năng hiển thị và độ tương phản trên một phổ rộng các tình huống thiếu sáng, bao gồm chiếu sáng không đồng đều, bóng tối cực hạn, ngược sáng và cảnh đêm. Ngoài ra, LLIE còn nỗ lực khắc phục các khiếm khuyết như nhiễu (noise), hiện tượng tạo tác (artifacts) và biến dạng màu sắc. Những thách thức này phát sinh trong điều kiện bóng tối hoặc qua quá trình tăng cường chiếu sáng, ảnh hưởng đến cả nhận thức thị giác của con người lẫn các tác vụ xuôi dòng (downstream tasks) như phát hiện đối tượng và phân đoạn cảnh.

∗ X. Liu, Z. Wu, A. Li, F. Vasluianu, Y. Zhang, S. Gu, L. Zhang, C. Zhu và R. Timofte là các nhà tổ chức thử thách, trong khi các tác giả khác tham gia thử thách. Mỗi đội mô tả phương pháp riêng của họ trong báo cáo. Phụ lục A bao gồm các đội và cơ quan công tác của tác giả.  
Trang web NTIRE 2024: https://cvlai.net/ntire/2024.  
Mã nguồn: https://github.com/AVC2-UESTC/NTIRE24-LLE/

Khi công nghệ học sâu (deep learning) cải tiến vượt bậc, những tiến bộ vượt trội trong LLIE là rất ấn tượng. Tuy nhiên, các phương pháp tiên tiến hiện tại [8, 34, 39, 47, 55, 72, 78] không chỉ gặp khó khăn trong việc thích ứng với các điều kiện thiếu sáng phức tạp và biến đổi mà còn đối mặt với những thách thức lớn khi triển khai trên các thiết bị cấp tiêu dùng như điện thoại thông minh và máy ảnh. Điều này chủ yếu bị giới hạn bởi các hạn chế của những bộ dữ liệu hiện tại [7, 71] vốn thiếu sự đa dạng về cảnh (đặc biệt là không đủ cảnh đêm), độ phân giải thấp và điều kiện ánh sáng quá đơn giản. Hơn nữa, độ phức tạp cao của các mô hình [8, 38, 39, 69, 74] cản trở khả năng xử lý các hình ảnh có độ phân giải siêu cao thường được chụp bằng điện thoại thông minh.

Để giải quyết những thách thức kể trên, chúng tôi đã khởi xướng Thử thách Tăng cường Ảnh Thiếu sáng đầu tiên tại hội thảo Xu hướng Mới trong Phục hồi và Tăng cường Ảnh 2024 (NTIRE 2024). Mục tiêu của thử thách này là thúc đẩy tư duy đổi mới và khám phá các giải pháp cải thiện đáng kể chất lượng hình ảnh trong các điều kiện thiếu sáng khác nhau. Để đạt được mục tiêu này, chúng tôi đã xây dựng một bộ dữ liệu LLIE đặc trưng bởi phạm vi cảnh rộng lớn, bao gồm nhiều điều kiện thiếu sáng đa dạng. Những hình ảnh này bao gồm các địa điểm trong nhà và ngoài trời trong cả điều kiện ban ngày và ban đêm, với thử thách tập trung vào việc nâng cao chất lượng hình ảnh trên các bối cảnh đa dạng này.

Tóm lại, thử thách này nhằm thiết lập một bộ tiêu chuẩn đánh giá (benchmark) mới cho LLIE đồng thời làm nổi bật các thách thức và câu hỏi nghiên cứu cụ thể trong lĩnh vực này. Chúng tôi hy vọng rằng cuộc thi sẽ truyền cảm hứng cho cộng đồng nghiên cứu khám phá các vấn đề cấp bách này và xác định những xu hướng mới nổi. Hơn nữa, thử thách này là một trong các thử thách liên kết của Hội thảo NTIRE 2024 về: khử sương mù dày đặc và không đồng nhất [1], kết xuất nhiếp ảnh ban đêm [4], tăng cường ảnh nén mù [73], loại bỏ bóng đổ [67], siêu phân giải hiệu quả [64], siêu phân giải ảnh (×4) [20], siêu phân giải ảnh trường ánh sáng [70], siêu phân giải ảnh lập thể [68], ước lượng độ sâu HR từ ảnh bề mặt phản xạ và trong suốt [77], phục hồi và tăng cường ảnh chụp bù sáng (bracketing) [81], đánh giá chất lượng ảnh chân dung [17], đánh giá chất lượng cho nội dung do AI tạo ra [48], phục hồi bất kỳ mô hình hình ảnh nào (RAIM) trong tự nhiên [45], siêu phân giải ảnh RAW [24], đánh giá chất lượng video UGC dạng ngắn [44], tăng cường thiếu sáng [49], và thử thách căn chỉnh chùm ảnh RAW và ISP.

## 2. Thử thách NTIRE 2024 về Tăng cường Ảnh Thiếu sáng (NTIRE 2024 Low Light Enhancement Challenge)

Mục tiêu của thử thách này gồm ba phần: (1) thúc đẩy nghiên cứu trong lĩnh vực tăng cường ảnh thiếu sáng, (2) tạo điều kiện so sánh có hệ thống giữa các phương pháp luận khác nhau, và (3) cung cấp một diễn đàn cho cả giới học thuật và doanh nghiệp tương tác, thảo luận và tiềm năng xây dựng các mối quan hệ hợp tác. Phần này đi sâu vào các khía cạnh chi tiết của thử thách.

Mặc dù một số bộ dữ liệu thiếu sáng, chẳng hạn như LOL [71] và MIT-Adobe FiveK [7], đã được áp dụng rộng rãi trong lĩnh vực này, chúng vẫn bộc lộ những hạn chế đã đề cập trước đó, bao gồm độ phân giải hạn chế, nội dung cảnh đơn điệu và mức độ chiếu sáng đồng nhất. Những yếu tố này thường hạn chế khả năng tổng quát hóa của các mô hình tiên tiến nhất [8, 39, 47, 55, 72, 78], đặt ra những thách thức đáng kể trong việc thích ứng với các điều kiện thiếu sáng đa dạng, đặc biệt là khi triển khai trên các thiết bị tiêu dùng như điện thoại thông minh và máy ảnh. Để giải quyết những vấn đề này, thử thách lần này giới thiệu một loạt các kịch bản thi đấu phong phú, bao gồm nhiều điều kiện ánh sáng như môi trường mờ tối, bóng tối cực hạn, chiếu sáng không đồng đều, ngược sáng và cảnh đêm, áp dụng cho cả bối cảnh trong nhà và ngoài trời vào ban ngày lẫn ban đêm, với độ phân giải hình ảnh lên đến 4K và hơn thế nữa. Cụ thể, bộ dữ liệu bao gồm 230 cảnh huấn luyện, cùng với 35 cảnh xác thực (validation) và 35 cảnh kiểm thử (testing). Các hình ảnh dữ liệu chuẩn thực tế (ground truth - GT) cho cả tập xác thực và kiểm thử đều được giữ kín với người tham gia trong suốt thử thách. Thông tin chi tiết hơn về bộ dữ liệu sẽ được cung cấp trong các công trình tiếp theo.

**Thống kê xếp hạng (Ranking statistic):** Trong thử thách này, chúng tôi chủ yếu sử dụng tỷ số tín hiệu trên nhiễu đỉnh (PSNR), độ tương đồng cấu trúc (SSIM) và Độ tương đồng mảnh ảnh cảm nhận học được (Learned Perceptual Image Patch Similarity - LPIPS) [80] làm tiêu chí so sánh các mô hình được gửi bởi người tham gia. Do LPIPS là một chỉ số đánh giá cảm nhận dựa trên học máy và cuộc thi của chúng tôi tập trung chủ yếu vào các đánh giá định lượng, chúng tôi sử dụng LPIPS như một công cụ đánh giá bổ sung khi các đánh giá định lượng của hai phương pháp không thể phân biệt được. Như được liệt kê trong Bảng 1, "Thứ hạng chung cuộc" (Final Rank) đại diện cho một chỉ số tổng hợp, được tính toán thông qua tổng có trọng số của PSNR (60%) và SSIM (40%). Cách tiếp cận này mang lại một đánh giá toàn diện về hiệu quả của từng giải pháp trong việc tăng cường các điều kiện thiếu sáng.

**Các giai đoạn của thử thách (Challenge phases):**  
(1) *Giai đoạn phát triển và xác thực (Development and validation phase):* Những người tham gia được cấp quyền truy cập vào 230 cặp hình ảnh huấn luyện và 35 hình ảnh đầu vào xác thực từ bộ dữ liệu do chúng tôi xây dựng. Đáng chú ý là các hình ảnh GT cho tập xác thực đã được ẩn khỏi người tham gia. Người tham gia có cơ hội gửi kết quả tăng cường của mình lên máy chủ đánh giá, nơi tính toán PSNR và SSIM cho các hình ảnh tăng cường do mô hình của họ tạo ra và cung cấp phản hồi ngay lập tức.  
(2) *Giai đoạn kiểm thử (Testing phase):* Người tham gia có quyền truy cập vào 35 hình ảnh thiếu sáng kiểm thử từ bộ dữ liệu đã xây dựng, với các hình ảnh chuẩn thực tế (ground truth) vẫn chưa được tiết lộ. Các bài nộp kết quả tăng cường được đưa lên máy chủ đánh giá CodaLab, kèm theo email gửi tới ban tổ chức bao gồm mã nguồn và bảng thông tin kỹ thuật (factsheet). Ban tổ chức sau đó đã xác minh và thực thi mã nguồn được cung cấp để rút ra kết quả cuối cùng, vốn được chia sẻ với những người tham gia khi kết thúc thử thách.

Bảng 1. Đánh giá và Xếp hạng trong Thử thách Tăng cường Ảnh Thiếu sáng NTIRE 2024. Bảng này trình bày sự so sánh toàn diện về các giải pháp của các đội tham gia qua nhiều chỉ số: PSNR, SSIM và LPIPS. "Rank PSNR" và "Rank SSIM" cho biết thứ hạng tương ứng của những người tham gia dựa trên hiệu suất của họ theo các chỉ số PSNR và SSIM trên tập dữ liệu kiểm thử của thử thách. "Final Rank" đại diện cho chỉ số tổng hợp, được suy ra từ tổng có trọng số của PSNR (60%) và SSIM (40%), cung cấp đánh giá tổng thể về hiệu quả của từng giải pháp trong việc tăng cường thiếu sáng.

| Đội (Team) | PSNR | SSIM | LPIPS | Hạng PSNR | Hạng SSIM | Hạng Chung cuộc |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| SYSU-FVL-T2 | 25.52 | 0.8637 | 0.1221 | 1 | 1 | 1 |
| Retinexformer [8] | 25.30 | 0.8525 | 0.1424 | 2 | 4 | 2 |
| DH-AISP | 24.97 | 0.8528 | 0.1235 | 3 | 3 | 3 |
| NWPU-DiffLight | 24.78 | 0.8556 | 0.1673 | 6 | 2 | 4 |
| GiantPandaCV | 24.83 | 0.8474 | 0.1353 | 5 | 7 | 5 |
| LVGroup.HFUT | 24.88 | 0.8395 | 0.1371 | 4 | 10 | 6 |
| Try ltry8 | 24.49 | 0.8483 | 0.1359 | 8 | 6 | 7 |
| Pixel warrior | 24.74 | 0.8416 | 0.1514 | 7 | 9 | <<<MATH_TOKEN_0008>>> |
| HuiT | 24.13 | 0.8484 | 0.1436 | 10 | 5 | 9 |
| X-LIME | 24.28 | 0.8446 | 0.1298 | 9 | <<<MATH_TOKEN_0009>>> | 10 |
| Image Lab | 23.63 | 0.8235 | 0.1673 | 11 | 12 | 11 |
| dgzzqteam | 23.28 | 0.8385 | 0.1406 | 12 | 11 | 12 |
| Cidaut AI (InstructIR [23]) | 23.07 | 0.8075 | 0.1559 | 13 | 16 | 13 |
| <<<MATH_TOKEN_0010>>> | 22.93 | 0.8097 | 0.1592 | 14 | 15 | 14 |
| ataza | 22.51 | 0.8161 | 0.1404 | 18 | 13 | 15 |
| KLETech-CEVI.LowlightHypnotise | 22.85 | 0.7828 | 0.1823 | 15 | 18 | 16 |
| 221B | 22.04 | 0.8141 | 0.1084 | 19 | 14 | 17 |
| KLETech-CEVI_Dark Knights | 22.76 | 0.7843 | 0.1806 | 17 | 17 | 18 |
| BFU-LL | 22.78 | 0.7792 | 0.1826 | 16 | 19 | 19 |
| SVNIT.NTNU | <<<MATH_TOKEN_0011>>> | 0.7718 | 0.3089 | 20 | 20 | 20 |
| yanhailong | <<<MATH_TOKEN_0012>>> | 0.6881 | 0.3133 | 21 | 22 | 21 |
| Mishka | 18.19 | 0.7161 | 0.2712 | 22 | 21 | 22 |

## 3. Kết quả Thử thách (Challenge Results)

Kết quả của thử thách tăng cường ảnh thiếu sáng được trình bày chi tiết trong Bảng 1, nơi đánh giá và xếp hạng hiệu suất của 22 đội. Đáng chú ý, một đội là AiRiA Vision đã tự nguyện rút khỏi bảng xếp hạng do các vấn đề liên quan đến thiết kế mô hình của họ. Việc đánh giá tận dụng hai chỉ số hiệu suất chính: PSNR và SSIM. Các chỉ số được tính toán dựa trên tập kiểm thử bao gồm 35 đầu vào từ bộ dữ liệu đã xây dựng, qua đó đảm bảo tính toàn vẹn của thử thách và giảm thiểu rủi ro quá khớp (overfitting) với tập xác thực.

Các đội đứng đầu trong thử thách sở hữu các giá trị PSNR và SSIM cao hơn, biểu thị hiệu suất vượt trội, trong khi các đội xếp hạng thấp hơn thể hiện các giá trị thấp hơn, cho thấy hiệu suất chưa tối ưu. Đáng chú ý, có hai đội đã đạt được PSNR trên 25 dB, đáp ứng các kỳ vọng trước đó của chúng tôi đối với chỉ số này. Để biết thêm thông tin chi tiết về các phương pháp tăng cường thiếu sáng được áp dụng, vui lòng tham khảo Phần 4, nơi thảo luận về các giải pháp cụ thể do từng đội cung cấp.

Do độ phân giải siêu cao (4K trở lên) của các hình ảnh đầu vào, nhiều đội đã lựa chọn các chiến lược đa tỷ lệ (multi-scale strategies) để thực hiện tăng cường. Mặc dù chúng đã giảm thiểu phần nào mức tiêu thụ tính toán, nhưng hiện tại, hầu như tất cả các mô hình đều không thể thực hiện suy luận trên một GPU thông thường, ví dụ như GPU có bộ nhớ 12G. Đối với cuộc thi tiếp theo, chúng tôi sẽ xem xét việc đưa vào NIQE [59] cùng với các chỉ số đo lường hiệu quả mô hình, chẳng hạn như thời gian suy luận, số lượng tham số mô hình, độ phức tạp tính toán (FLOPs) và mức tiêu thụ bộ nhớ. Điều này sẽ thúc đẩy việc ứng dụng tăng cường thiếu sáng độ phân giải siêu cao trên điện thoại thông minh.
