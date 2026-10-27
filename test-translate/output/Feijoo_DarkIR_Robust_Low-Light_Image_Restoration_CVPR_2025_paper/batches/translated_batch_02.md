Mô-đun chú ý không gian tương tự NAFBlock [7] với một khối phần dư nghịch đảo (inverted residual block) theo sau bởi cơ chế chú ý kênh đơn giản hóa (simplified channel attention - SCA). Thay vì sử dụng các hàm kích hoạt phi tuyến, chúng tôi áp dụng cơ chế cổng đơn giản (simple gating), cho phép mô hình trích xuất các thông tin không gian ý nghĩa phục vụ cho quá trình tăng cường trong miền tần số.

Theo các nghiên cứu trước đây [33, 44], thông tin liên quan đến điều kiện chiếu sáng của hình ảnh chủ yếu phụ thuộc vào phổ biên độ (amplitude) trong miền tần số. Để tăng cường thành phần này, chúng tôi áp dụng Biến đổi Fourier Nhanh (FFT) và chỉ thao tác trên biên độ của nó. Sau thao tác này, chúng tôi chuyển ngược về miền không gian bằng Biến đổi Fourier Nhanh Ngược (IFFT). Mạng Fre-MLP đóng vai trò như một cơ chế chú ý bổ sung. Trong ngữ cảnh này, MLP hoạt động trên biên độ đem lại nhiều lợi ích vượt trội hơn so với hoạt động trong miền không gian (ví dụ: channel MLP [56]).

Bộ mã hóa sử dụng các phép tích chập có bước nhảy (strided convolutions) để giảm mẫu các đặc trưng. Sau mỗi cấp độ, các đặc trưng bị giảm một nửa độ phân giải không gian ban đầu, điều này đồng nghĩa với việc chúng ta có thể bố trí nhiều khối mã hóa hơn ở các cấp độ sâu mà không làm gia tăng đáng kể số lượng phép tính.

Cuối cùng, bộ mã hóa sẽ cung cấp các đặc trưng đã được tăng cường ánh sáng cho bộ giải mã, cùng với một ước tính độ phân giải thấp của ảnh sạch x. Ảnh độ phân giải thấp $\hat{x}_{\downarrow 8}$ này được ước tính thông qua tổ hợp tuyến tính các đặc trưng sâu của bộ mã hóa, có độ phân giải thấp hơn 8 lần ($8\times$) so với ảnh gốc. Dù là một ước tính kích thước nhỏ, đặc tính chiếu sáng (và biên độ) luôn nhất quán qua các thang đo tỷ lệ khác nhau [28].

### 3.2. Bộ giải mã khử mờ (Deblurring Decoder)

Khối giải mã (**DBlock**) tập trung vào các phép biến đổi không gian. Đầu vào của bộ giải mã là một biểu diễn sâu của <<<MATH_TOKEN_0013>>>, do đó chúng ta có thể giả định: (1) bộ giải mã cần tập trung vào việc nâng mẫu cho ước tính khởi tạo này, (2) bộ giải mã cần tập trung vào việc khử nhòe mờ và cải thiện độ sắc nét, vì độ chiếu sáng đã được hiệu chỉnh trọn vẹn bởi bộ mã hóa. Trong khối này, chúng tôi tiếp tục duy trì cấu trúc Metaformer [56]:

<<<MATH_TOKEN_0014>>>

<<<MATH_TOKEN_0015>>>

Được truyền cảm hứng từ Cơ chế chú ý Kernel lớn (Large Kernel Attention - LKA) [17], chúng tôi phát triển **Mô-đun chú ý không gian giãn nở (Dilated-Spatial Attention Module - Di-SpAM)**. Khác với LKA [17], chúng tôi khai thác các đặc trưng ở 3 cấp độ khác nhau bằng cách sử dụng ba nhánh tích chập theo chiều sâu giãn nở (dilated depth-wise convolutions) với hệ số giãn nở (dilation factors) lần lượt là 1, 4 và 9. Các thuộc tính từ ba nhánh được hợp nhất lại, sau đó chúng tôi áp dụng cơ chế chú ý kênh đơn giản hóa (SCA) để tiếp tục tăng cường đặc trưng. Cuối cùng, chúng tôi sử dụng mạng MLP kết hợp các cổng đơn giản (simple gates) thay cho các hàm kích hoạt thông thường [7].

### 3.3. Hàm mất mát (Loss Function)

Bên cạnh thiết kế khối mạng mới, hàm mất mát đóng vai trò then chốt giúp tối đa hóa tiềm năng của phương pháp. Chúng tôi kết hợp hàm mất mát biến dạng (distortion loss) và mất mát tri giác (perceptual loss) để tối ưu hóa mô hình <<<MATH_TOKEN_0016>>>.

Đầu tiên, để đảm bảo độ trung thực cao (độ biến dạng thấp), chúng tôi sử dụng <<<MATH_TOKEN_0017>>> định nghĩa là: <<<MATH_TOKEN_0018>>>, trong đó <<<MATH_TOKEN_0019>>> và <<<MATH_TOKEN_0020>>> lần lượt là ảnh tăng cường và ảnh chuẩn thực tế (ground-truth / clean). Do đó, <<<MATH_TOKEN_0021>>> là hàm mất mát <<<MATH_TOKEN_0022>>> (chuẩn $L_1$).

Để đảm bảo độ tương đồng cảm nhận, chúng tôi tích hợp hàm mất mát <<<MATH_TOKEN_0023>>> dựa trên LPIPS [60] sử dụng mạng VGG19 [43] nhằm tính toán khoảng cách đặc trưng giữa các hình ảnh:

<<<MATH_TOKEN_0024>>>

Việc sử dụng hàm mất mát này đảm bảo mạng sẽ tạo ra hình ảnh dễ nhìn và tiệm cận với ảnh tham chiếu sạch. Học hỏi từ [41], chúng tôi cũng đưa vào hàm mất mát cạnh gradient ($\nabla$ edge loss):

<<<MATH_TOKEN_0025>>>

nhằm thúc đẩy tính nhất quán và độ chính xác trong việc tái tạo các đường biên cạnh (thành phần tần số cao).

Cuối cùng, tương tự như LEDNet [65], chúng tôi bổ sung <<<MATH_TOKEN_0027>>> – một hàm mất mát dẫn hướng kiến trúc để đảm bảo bộ mã hóa tập trung đúng vào nhiệm vụ tăng cường ánh sáng yếu. Mất mát này hoạt động trên đầu ra được nâng mẫu của bộ mã hóa <<<MATH_TOKEN_0028>>>:

<<<MATH_TOKEN_0029>>>

so sánh trực tiếp với ảnh tham chiếu <<<MATH_TOKEN_0030>>>. Lưu ý rằng <<<MATH_TOKEN_0031>>> biểu thị phép nâng độ phân giải $8\times$ đối với đầu ra bộ mã hóa thông qua nội suy song tuyến tính (bilinear interpolation).

Hàm mất mát toàn phần hoàn chỉnh là:

<<<MATH_TOKEN_0032>>>

Các hằng số <<<MATH_TOKEN_0033>>>, $\lambda_{pe}$ và $\lambda_{ed}$ là các trọng số mất mát được thiết lập thực nghiệm lần lượt là 1, <<<MATH_TOKEN_0035>>> ($10^{-2}$) và 50.

---

### 4. Kết quả thực nghiệm (4. Experimental Results)

#### 4.1. Các tập dữ liệu (Datasets)

Để huấn luyện mô hình và đánh giá năng lực phục hồi hình ảnh mờ thiếu sáng, chúng tôi sử dụng tập dữ liệu **LOLBlur** [65]. Mặc dù có các tập dữ liệu khác cho tác vụ này như NBDN [6], LOLBlur cung cấp một tập dữ liệu tổng hợp quy mô lớn được xây dựng bằng một quy trình mô phỏng tinh vi.

- **LOLBlur:** Gồm 10.200 cặp ảnh huấn luyện và 1.800 cặp ảnh kiểm tra. Mặc dù là dữ liệu tổng hợp, nó được tạo ra theo phương thức chân thực [65]: tổng hợp độ mờ bằng cách trung bình hóa các khung hình và làm tối ảnh chụp điều kiện chuẩn bằng EC-Zero-DCE (một biến thể của Zero-DCE [16]). Chúng tôi sử dụng biến thể bao gồm nhiễu cảm biến thực, giúp mô hình hoạt động hiệu quả hơn trong các điều kiện thực tế đầy thử thách.
- **Real-LOLBlur:** Tập kiểm tra thực tế gồm 482 ảnh đêm mờ nhòe thực tế được trích từ RealBlur [40] để kiểm chứng khả năng tổng quát hóa của phương pháp đề xuất. Các ảnh này không có ảnh chuẩn thực tế (ground-truth) vì được chụp tự do ngoài đời thực.
- **LOLv2 (Real):** Tập dữ liệu thực tế gồm 689 cặp ảnh tối/sáng huấn luyện và 100 cặp kiểm tra. Đây là phiên bản mở rộng của LOL [47]. Chúng tôi cũng sử dụng **LOLv2-Synthetic** gồm 900 cặp huấn luyện và 100 cặp kiểm định.
- **LSRW:** Chứa ảnh từ máy ảnh DSLM Nikon và điện thoại thông minh Huawei. Tập LSRW-Nikon gồm 3.150 cặp huấn luyện và 20 cặp kiểm tra. Tập LSRW-Huawei gồm 2.450 cặp huấn luyện và 30 cặp kiểm định.

#### 4.2. Kết quả đánh giá (Results)

Chúng tôi đánh giá định lượng và định tính DarkIR trên tập LOLBlur [65]. Nhóm nghiên cứu huấn luyện lại một số phương pháp SOTA đa dụng trên LOLBlur và so sánh chúng với LEDNet [65] cùng mạng đề xuất. Các phương pháp cơ sở được phân loại thành: (1, 2) các phương pháp zero-shot huấn luyện cho trường hợp thực tế, và (3) các phương pháp được tinh chỉnh riêng cho tác vụ này.

1. **LLIE $\to$ Deblurring:** Chúng tôi xem xét Zero-DCE [16], RUAS [30] và RetinexFormer [3] làm mô hình LLIE, tiếp nối bởi một mạng khử mờ như MIMO-UNet [8] hoặc NAFNet [7].
2. **Deblurring $\to$ LLIE:** Sử dụng các mô hình khử mờ cơ sở như DeblurGAN-v2 [25] huấn luyện trên RealBlur [40], MIMO-UNet [8] hoặc NAFNet [7] huấn luyện trên GoPro [38]. Sau đó áp dụng Zero-DCE [16] và RetinexFormer [3] để tăng cường độ sáng.
3. **Huấn luyện đầu-cuối trên tập dữ liệu LOLBlur:** Huấn luyện lại các mô hình LLIE gồm KinD++ [61], DRBN [54] và RetinexFormer [3], cùng 4 mạng khử mờ: DeblurGAN-v2 [25], NAFNet [9], MIMO-UNet [8] và Restormer [57].

**Tiêu chí đánh giá (Evaluation Metrics):** Sử dụng các thang đo chất lượng truyền thống (độ biến dạng) PSNR và SSIM trên tập dữ liệu tổng hợp LOLBlur. Đánh giá chất lượng tri giác thông qua chỉ số LPIPS [60] giữa ảnh tham chiếu và ảnh tái tạo.

| Phương pháp | PSNR (dB) ↑ | SSIM ↑ | LPIPS ↓ | Tham số (M) ↓ | MACs (G) ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| KinD++ [61] | 21.26 | 0.753 | 0.359 | 1.20 | 34.99 |
| DRBN [54] | 21.78 | 0.768 | 0.325 | 0.60 | 48.61 |
| DeblurGAN-v2 [25] | 22.30 | 0.745 | 0.356 | 60.90 | - |
| MIMO [8] | 22.41 | 0.835 | 0.262 | 6.80 | 67.25 |
| NAFNet [9] | 25.36 | 0.882 | 0.158 | 12.05 | 12.30 |
| LEDNet [65] | 25.74 | 0.850 | 0.224 | 7.40 | 38.65 |
| RetinexFormer [3] | 26.02 | 0.887 | 0.181 | 1.61 | 15.57 |
| Restormer [57] | 26.72 | **0.902** | **0.133** | 26.13 | 144.25 |
| **DarkIR-m (Ours)** | <u>27.00</u> | 0.883 | 0.162 | 3.31 | **7.25** |
| **DarkIR-l (Ours)** | **27.30** | <u>0.898</u> | <u>0.137</u> | 12.96 | <u>27.19</u> |

Bảng 1. Đánh giá định lượng trên tập dữ liệu LOLBlur. DarkIR đạt kết quả hiện đại nhất (SOTA) mới về cả chỉ số biến dạng lẫn chỉ số tri giác. Đặc biệt, mô hình có số tham số ít hơn 55% so với LEDNet [65] và ít hơn 88% so với Restormer [57], yếu tố mang tính quyết định trên các thiết bị hạn chế tài nguyên bộ nhớ. Bảng này tổng hợp các kết quả phân tích trước đây [65] và bổ sung các mô hình được huấn luyện lại mới. Kết quả tốt nhất được in đậm (**bold**), tốt nhì được gạch chân (<u>underline</u>).

![Hình 3. So sánh định tính trên tập dữ liệu LOLBlur (các mẫu tổng hợp từ tập kiểm tra).](figures/figure_03.png)

Hình 3. So sánh định tính trên tập dữ liệu LOLBlur (các mẫu tổng hợp từ tập kiểm tra).

| Nhóm quy trình | Kết hợp mô hình | PSNR (dB) ↑ | SSIM ↑ | LPIPS ↓ |
| :--- | :--- | :---: | :---: | :---: |
| **1. LLIE $\to$ Khử mờ** | Zero-DCE [16] $\to$ MIMO [8] | 17.68 | 0.542 | 0.510 |
| | RUAS [30] $\to$ MIMO [8] | 17.81 | 0.569 | 0.523 |
| | RetinexFormer [3] $\to$ NAFNet [7] | 17.16 | 0.673 | 0.392 |
| **2. Khử mờ $\to$ LLIE** | Chen [5] $\to$ Zero-DCE [16] | 17.02 | 0.502 | 0.516 |
| | DeblurGAN-v2 [25] $\to$ Zero-DCE [16] | 18.33 | 0.589 | 0.476 |
| | MIMO [8] $\to$ Zero-DCE [16] | 17.52 | 0.570 | 0.498 |
| | NAFNet [7] $\to$ RetinexFormer [3] | 14.66 | 0.500 | 0.465 |
| **Đầu-cuối (End-to-End)** | **DarkIR-m (Ours)** | **27.00** | **0.883** | **0.162** |

Bảng 2. Đánh giá định lượng bổ sung trên tập dữ liệu LOLBlur với các quy trình tăng cường 2 bước (Khử mờ + LLIE).

![Hình 4. So sánh trực quan bổ sung trên tập dữ liệu LOLBlur [65] với các quy trình 2 bước. DarkIR tạo ra hình ảnh sắc nét hơn nhiều với kết quả trực quan đẹp mắt. (Phóng to để có góc nhìn tốt nhất).](figures/figure_04.png)

Hình 4. So sánh trực quan bổ sung trên tập dữ liệu LOLBlur [65] với các quy trình 2 bước. DarkIR tạo ra hình ảnh sắc nét hơn nhiều với kết quả trực quan đẹp mắt. (Phóng to để có góc nhìn tốt nhất).

**Kết quả định lượng và định tính:** Trong Bảng 1, chúng tôi so sánh với các phương pháp được tinh chỉnh riêng cho tác vụ này. DarkIR vượt trội hơn SOTA tiền nhiệm LEDNet [65] tới +1dB PSNR và giảm chỉ số LPIPS xuống một nửa. Bảng 1 cũng chứng minh DarkIR hoạt động tốt hơn hầu hết các phương pháp đa dụng khác, đồng thời giảm số lượng tham số và chi phí tính toán. Hình 3 minh chứng trực quan cho các kết quả này.

Trong Bảng 2, chúng tôi so sánh với các quy trình 2 bước (zero-shot), với sự áp đảo rõ rệt của DarkIR. Hình 4 so sánh DarkIR với các quy trình 2 bước, cho thấy rõ độ chi tiết và độ sắc nét vượt trội.

**Kết quả đa nhiệm (Multi-Task Results):** Chúng tôi cũng huấn luyện mô hình cho các mục đích phục hồi thiếu sáng trong thực tế, kết hợp các tập dữ liệu LOLBlur, LOLv2-Real, LOLv2-Synthetic và LSRW (tương tự các phương pháp phục hồi all-in-one [11, 27, 39, 59]). Kết quả thể hiện trong Bảng 3 và Bảng 4. Với tư cách là một phương pháp đa nhiệm, **DarkIR-mt** vượt trội hơn các phương pháp LLIE trước đây, đồng thời chống chịu tốt với hiện tượng nhòe mờ (các phương pháp trước đây chỉ mạnh mẽ trước biến đổi ánh sáng và nhiễu). Mặc dù vậy, hiệu năng trên LOLBlur đạt 26.62 dB, chịu mức suy giảm nhẹ -0.4dB PSNR. Hình 5 và Hình 6 lần lượt minh họa các kết quả này trên tập dữ liệu LSRW và LOLv2-Real.
