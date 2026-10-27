### 4.3. Đánh giá trên dữ liệu thực tế (Evaluation on Real Data)

Chúng tôi sử dụng tập dữ liệu **Real-LOLBlur** [65] để đánh giá tính vững chắc của phương pháp đề xuất trong các tình huống thực tế. Do không có ảnh chuẩn thực tế (ground-truth) cho các ảnh kiểm tra này, chúng tôi áp dụng các thước đo đánh giá chất lượng ảnh mù (blind quality assessment metrics) nổi tiếng. Các kết quả trên những tập dữ liệu LLIE thực tế (không theo cặp) khác được trình bày chi tiết trong phần phụ lục.

**Tiêu chí đánh giá tri giác (Perceptual Metrics):** Chúng tôi sử dụng các phương pháp đánh giá chất lượng hình ảnh hiện đại gồm: MUSIQ [23], NRQM [34] và NIQE [36]. Tuân theo các nghiên cứu đi trước, chúng tôi lựa chọn mô hình MUSIQ được huấn luyện trên tập dữ liệu KonIQ-10k, vốn tập trung chuyên sâu vào việc đánh giá độ tương phản màu sắc và độ sắc nét – rất tương thích với bài toán của chúng tôi. Chúng tôi sử dụng bản cài đặt pyiqa của các thước đo này.

**Đánh giá định lượng:** Như thể hiện trong Bảng 5, mô hình DarkIR đề xuất đạt điểm chất lượng tri giác rất cạnh tranh xét theo cả ba thang đo, chứng minh phương pháp của chúng tôi hoạt động hài hòa và đồng điệu với cảm nhận thị giác của con người.

| Phương pháp | PSNR (dB) ↑ | SSIM ↑ |
| :--- | :---: | :---: |
| RetinexNet [47] | 15.906 | 0.3725 |
| FIDE [51] | 17.669 | 0.5485 |
| DRBN [54] | 16.149 | 0.5422 |
| KinD [61] | 16.472 | 0.4929 |
| STAR [50] | 14.608 | 0.5039 |
| EnGAN [22] | 16.311 | 0.4697 |
| ZDCE [16] | 15.834 | 0.4664 |
| RUAS [30] | 14.437 | 0.4276 |
| SCI [35] | 15.017 | 0.4846 |
| **DarkIR-mt (Ours)** | **18.930** | **0.5830** |

Bảng 3. Các chỉ số đánh giá trên tập dữ liệu LSRW (50 hình ảnh kiểm tra từ thiết bị Huawei và Nikon) [19]. Tất cả các giá trị tham chiếu được kế thừa từ [35, 53].

![Hình 5. Kết quả định tính trên tập dữ liệu thực tế LSRW-Huawei [19]. Chúng tôi cung cấp thêm các mẫu trong phần tài liệu bổ sung.](figures/figure_05.png)

Hình 5. Kết quả định tính trên tập dữ liệu thực tế LSRW-Huawei [19]. Chúng tôi cung cấp thêm các mẫu trong phần tài liệu bổ sung.

![Hình 6. Kết quả định tính so sánh với phương pháp hiện đại nhất RetinexFormer [3] trên LOLv2-Real.](figures/figure_06.png)

Hình 6. Kết quả định tính so sánh với phương pháp hiện đại nhất RetinexFormer [3] trên LOLv2-Real.

| Phương pháp | MACs (G) ↓ | Tham số (M) ↓ | LOLv2-Real PSNR ↑ | LOLv2-Real SSIM ↑ | LOLv2-Syn PSNR ↑ | LOLv2-Syn SSIM ↑ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| UFormer [46] | 12.00 | 5.29 | 18.82 | 0.771 | 19.66 | 0.871 |
| RetinexNet [47] | 587.47 | 0.84 | 15.47 | 0.567 | 17.13 | 0.798 |
| EnGAN [22] | 61.01 | 114.35 | 18.23 | 0.617 | 16.57 | 0.734 |
| RUAS [30] | 0.83 | 0.003 | 18.37 | 0.723 | 16.55 | 0.652 |
| FIDE [51] | 28.51 | 8.62 | 16.85 | 0.678 | 15.20 | 0.612 |
| DRBN [54] | 48.61 | 5.27 | 20.29 | 0.831 | 23.22 | 0.927 |
| KinD [61] | 34.99 | 8.02 | 14.74 | 0.641 | 13.29 | 0.578 |
| Restormer [57] | 144.25 | 26.13 | 19.94 | 0.827 | 21.41 | 0.830 |
| MIRNet [58] | 785.00 | 31.76 | 20.02 | 0.820 | 21.94 | 0.876 |
| SNR-Net [52] | 26.35 | 4.01 | 21.48 | 0.849 | 24.14 | 0.928 |
| FourLLIE [44] | 5.80 | 0.120 | 21.60 | 0.847 | 24.17 | 0.917 |
| Retinexformer [3] | 15.57 | 1.61 | 22.80 | 0.840 | **25.67** | 0.930 |
| **DarkIR-mt (Ours)** | **7.25** | **3.31** | **23.87** | **0.880** | 25.54 | **0.934** |

Bảng 4. Kết quả trên tập dữ liệu LOLv2-Real [55] và LOLv2-Synthetic [55]. Mô hình đa nhiệm của chúng tôi (DarkIR-mt) đạt kết quả SOTA mới nhờ việc áp dụng chiến lược huấn luyện all-in-one và tích hợp năng lực khử mờ thiếu sáng, chứng minh hiệu quả vượt bậc của kiến trúc mạng đề xuất. Bảng được tổng hợp dựa trên [3, 44]. Độ phức tạp tính toán MACs được đo lường trên đầu vào kích thước $256 \times 256 \times 3$.

| Phương pháp | MUSIQ ↑ | NRQM ↑ | NIQE ↓ |
| :--- | :---: | :---: | :---: |
| RUAS $\to$ MIMO | 34.39 | 3.322 | 6.812 |
| MIMO $\to$ Zero-DCE | 28.36 | 3.697 | 6.892 |
| RetinexFormer [3] | 45.30 | 5.281 | **4.576** |
| NAFNet [7] | **50.22** | 4.940 | 5.123 |
| LEDNet [65] | 39.11 | **5.643** | 4.764 |
| Restormer [57] | 46.60 | 4.627 | 5.268 |
| **DarkIR-m (Ours)** | 48.36 | 4.983 | 4.998 |
| **DarkIR-l (Ours)** | **48.79** | 4.917 | 5.051 |

Bảng 5. Các chỉ số chất lượng tri giác trên bộ dữ liệu thực tế Real-LOLBlur [65].

**Đánh giá định tính:** Hình 7 thể hiện so sánh trực quan trên các hình ảnh ban đêm bị nhòe mờ thực tế từ Real-LOLBlur [65]. Các mẫu hình ảnh này minh chứng rõ nét tính vững chắc của cách tiếp cận của chúng tôi trong các tình huống thực tế có độ rung lắc do chuyển động tay cầm, nhiễu cảm biến, điểm ảnh bão hòa sáng và độ rọi cực thấp.

![Hình 7. So sánh định tính trên các khung cảnh đêm thực tế từ tập dữ liệu RealBlurLOL. (Phóng to để có góc nhìn tốt nhất).](figures/figure_07.png)

Hình 7. So sánh định tính trên các khung cảnh đêm thực tế từ tập dữ liệu RealBlurLOL. (Phóng to để có góc nhìn tốt nhất).

---

### 4.4. Nghiên cứu loại trừ (Ablation Study)

Bên cạnh các kết quả thực nghiệm chính, chúng tôi tiến hành ba nghiên cứu loại trừ (ablation study) về thiết kế mô hình và chiến lược huấn luyện:

Trong Bảng 6, chúng tôi so sánh các kết quả thu được khi thay đổi các cấu hình khối mạng khác nhau như NAFBlock, EBlock hoặc DBlock. Phần mô tả chỉ rõ những điều chỉnh đối với mạng, trong khi tất cả các thành phần khác được giữ nguyên tuyệt đối như mô hình đề xuất. Có thể thấy rõ ràng mô hình kết hợp của chúng tôi đạt kết quả cao nhất. Khác với mô hình đề xuất cuối cùng, toàn bộ các mô hình trong nghiên cứu loại trừ này được huấn luyện trên các vùng cắt (crop) 256px thay vì 384px, điều này giải thích vì sao kết quả tổng thể có phần thấp hơn. Chúng tôi cũng nghiên cứu cơ chế chú ý không gian của khối giải mã trong Bảng 7, nơi cơ chế nổi tiếng Large Kernel Attention (LKA) [17] được đưa lên bàn cân so sánh với Mô-đun Di-SpAM của chúng tôi. Cách tiếp cận của chúng tôi hoạt động vượt trội hơn đồng thời đòi hỏi ít tham số và phép tính hơn.

Trong Bảng 8, chúng tôi khám phá khả năng mở rộng quy mô (scalability) của mô hình bằng cách thay đổi kích thước vector nhúng kênh (channel embedding). Đúng như kỳ vọng, khi tăng kích thước không gian nhúng, hiệu năng tăng đều đặn. Theo thứ tự tăng dần về tham số, chúng tôi thử nghiệm các vector nhúng 16, 32 và 64 kênh. Chúng tôi nhận thấy sự cân bằng tối ưu giữa hiệu quả và hiệu năng nằm ở cấu hình nhúng 32 kênh (**DarkIR-m**).

Trong tài liệu bổ sung, chúng tôi trình bày thêm các nghiên cứu chuyên sâu khác về quá trình phát triển kiến trúc.

| Cấu hình khối mạng | Tham số ↓ (M) | MACs ↓ (G) | PSNR ↑ | SSIM ↑ | LPIPS ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| EBlock thay bằng NAFBlock | 3.12 | 7.69 | 26.51 | 0.8764 | 0.169 |
| EBlock có thêm Biến đổi Pha | 4.08 | 8.38 | 26.30 | 0.8710 | 0.179 |
| Toàn bộ dùng DBlock | 3.20 | 8.19 | 26.68 | 0.8760 | 0.170 |
| Toàn bộ dùng EBlock | 3.44 | 6.46 | 26.17 | 0.8630 | 0.187 |
| Toàn bộ dùng NAFBlock [7] | 3.04 | 7.29 | 26.24 | 0.8680 | 0.178 |
| DBlock thay bằng NAFBlock | 3.24 | 6.84 | 26.23 | 0.8640 | 0.185 |
| DBlock không có Depthwise phụ | 3.27 | 6.99 | 26.63 | 0.8750 | 0.174 |
| **DarkIR-m (Đề xuất)** | **3.31** | **7.25** | **26.90** | **0.8740** | **0.175** |

Bảng 6. Nghiên cứu loại trừ cấu hình khối mạng. Sự kết hợp giữa EBlock và DBlock mang lại hiệu năng tối ưu nhất.

| Cơ chế chú ý không gian | Tham số ↓ (M) | MACs ↓ (G) | PSNR ↑ | SSIM ↑ | LPIPS ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| LKA [17] | 4.06 | 9.14 | 26.45 | 0.876 | 0.172 |
| **Di-SpAM (DarkIR-m)** | **3.31** | **7.25** | **27.00** | **0.883** | **0.162** |

Bảng 7. Nghiên cứu loại trừ cơ chế chú ý không gian. So sánh LKA (Large Kernel Attention) [17] với Di-SpAM đề xuất cho các khối giải mã. MACs được tính toán trên đầu vào kích thước 256px.

| Biến thể mô hình (Số kênh) | Tham số ↓ (M) | MACs ↓ (G) | PSNR ↑ | SSIM ↑ | LPIPS ↓ |
| :--- | :---: | :---: | :---: | :---: | :---: |
| DarkIR-s (16 kênh) | 0.872 | 2.04 | 26.15 | 0.857 | 0.206 |
| **DarkIR-m (32 kênh)** | **3.31** | **7.25** | **27.00** | **0.883** | **0.162** |
| DarkIR-l (64 kênh) | 12.96 | 27.19 | 27.30 | 0.898 | 0.137 |

Bảng 8. Nghiên cứu loại trừ mở rộng kích thước chiều sâu kênh. Mô hình mở rộng quy mô hợp lý, tạo điều kiện thuận lợi để tùy biến triển khai dựa trên giới hạn bộ nhớ hoặc thời gian phản hồi.

---

### 4.5. Thảo luận về hiệu quả tính toán (Efficiency Discussion)

Nhờ sự phối hợp nhịp nhàng giữa EBlock và DBlock, chúng tôi đã giảm mạnh số lượng tham số mạng, đạt mức giảm ấn tượng **55% tham số** so với LEDNet [65] (SOTA tiền nhiệm) và **88%** so với Restormer [57] (phương pháp tốt thứ nhì). Sự cắt giảm này đi liền với sự giảm sút đáng kể về số lượng phép toán cần thiết để xử lý ảnh đầu vào. Với ảnh đầu vào kích thước 256px như các nghiên cứu trước [7], LEDNet tiêu thụ 33.74 GMACs và Restormer tiêu thụ 141.24 GMACs, trong khi DarkIR chỉ tiêu tốn **7.25 GMACs** – lưu ý rằng 1 MAC tương đương khoảng 2 FLOPs. Điều này đồng nghĩa với mức cắt giảm **4× số lượng phép tính** so với phương pháp SOTA trước đó và gần **20×** so với phương pháp tốt thứ nhì.

Do đó, DarkIR không chỉ dẫn đầu về chất lượng khử mờ thiếu sáng mà còn gọn nhẹ toàn diện, đánh dấu một bước tiến quan trọng hướng tới việc triển khai các mô hình phục hồi ảnh cao cấp trên các thiết bị có tài nguyên tính toán khiêm tốn.

---

### 5. Hạn chế (Limitations)

Mặc dù đã giảm mạnh yêu cầu tính toán trên thiết bị đích, việc sử dụng các phép tích chập theo chiều sâu (depth-wise convolutions) không phải lúc nào cũng tối ưu trên một số kiến trúc GPU do tính chất thiếu hụt cường độ số học (arithmetic intensity) [15]. Vì lý do này, thời gian suy luận thực tế của mô hình chưa giảm tương ứng theo tỷ lệ cắt giảm phép toán. Trong các công trình tương lai, chúng tôi sẽ nghiên cứu các giải pháp mới có khả năng dung hòa giữa yêu cầu tính toán thấp và thời gian suy luận siêu tốc.

---

### 6. Kết luận (Conclusion)

Chúng tôi đề xuất một mô hình vững chắc cho bài toán tăng cường và phục hồi hình ảnh thiếu sáng đa nhiệm. Mô hình **DarkIR** là một mạng nơ-ron hiệu năng cao và bền vững, có khả năng thực hiện đồng thời khử nhiễu, khử mờ và tăng cường ánh sáng yếu trên các khung cảnh chụp tối và ban đêm. DarkIR thiết lập kỷ lục SOTA mới trên các bộ dữ liệu tiêu chuẩn LOLBlur, LOLv2 và Real-LOLBlur, cho thấy khả năng tổng quát hóa xuất sắc trên ảnh đêm mờ ngoài đời thực đồng thời vận hành gọn nhẹ và hiệu quả hơn hẳn các phương pháp trước đây.

---

### Lời cảm ơn (Acknowledgements)

Công trình nghiên cứu này được tài trợ bởi các quỹ công của Tây Ban Nha thông qua Viện Cạnh tranh Doanh nghiệp Khu vực Castile León (Dự án MACS.2: *“Nghiên cứu công nghệ trong lĩnh vực di chuyển tự hành, kết nối, an toàn và bền vững”*). Nhóm tác giả chân thành cảm ơn Trung tâm Siêu máy tính Castile và León (SCAYLE, León, Tây Ban Nha) đã hỗ trợ tài nguyên GPU và môi trường huấn luyện mô hình.

---

### Tài liệu tham khảo (References)

1. A. Abdelhamed, S. Lin, and M. S. Brown. A high-quality denoising dataset for smartphone cameras. In *CVPR*, 2018.
2. M. Abdullah-Al-Wadud, M. H. Kabir, M. A. A. Dewan, and O. Chae. A dynamic histogram equalization for image contrast enhancement. *IEEE Trans. Consumer Electron.*, 2007.
3. Y. Cai, H. Bian, J. Lin, H. Wang, R. Timofte, and Y. Zhang. Retinexformer: One-stage retinex-based transformer for low-light image enhancement. In *ICCV*, 2023.
4. A. Chakrabarti. A neural approach to blind motion deblurring. In *ECCV*, 2016.
5. L. Chen, J. Zhang, S. Lin, F. Fang, and J. S. Ren. Blind deblurring for saturated images. In *CVPR*, 2021.
6. L. Chen, J. Zhang, J. Pan, S. Lin, F. Fang, and J. S. Ren. Learning a non-blind deblurring network for night blurry images. In *CVPR*, 2021.
7. L. Chen, X. Chu, X. Zhang, and J. Sun. Simple baselines for image restoration. In *ECCV*, 2022.
8. S.-J. Cho, S.-W. Ji, J.-P. Hong, S.-W. Jung, and S.-J. Ko. Rethinking coarse-to-fine approach in single image deblurring. In *ICCV*, 2021.
9. X. Chu, L. Chen, and W. Yu. Nafssr: Stereo image super-resolution using nafnet. In *CVPRW*, 2022.
10. M. V. Conde, S. McDonagh, M. Maggioni, A. Leonardis, and E. Pérez-Pellitero. Model-based image signal processors via learnable dictionaries. In *AAAI*, 2022.
11. M. V. Conde, G. Geigle, and R. Timofte. High-quality image restoration following human instructions. *arXiv:2401.16468*, 2024.
12. M. Delbracio, D. Kelly, M. S. Brown, and P. Milanfar. Mobile computational photography: A tour. *arXiv:2102.09000*, 2021.
13. M. Elad and A. Feuer. Restoration of a single super-resolution image from several blurred, noisy, and undersampled measured images. *IEEE TIP*, 1997.
14. Y. Feng, C. Zhang, P. Wang, P. Wu, Q. Yan, and Y. Zhang. You only need one color space: An efficient network for low-light image enhancement. *arXiv:2402.05809*, 2024.
15. A. Gholami, K. Kwon, B. Wu, Z. Tai, X. Yue, P. Jin, S. Zhao, and K. Keutzer. Squeezenext: Hardware-aware neural network design. In *CVPRW*, 2018.
16. C. Guo, C. Li, J. Guo, C. C. Loy, J. Hou, S. Kwong, and R. Cong. Zero-reference deep curve estimation for low-light image enhancement. In *CVPR*, 2020.
17. M.-H. Guo, C.-Z. Lu, Z.-N. Liu, M.-M. Cheng, and S.-M. Hu. Visual attention network. *Computational Visual Media*, 2023.
18. X. Guo, Y. Li, and H. Ling. Lime: Low-light image enhancement via illumination map estimation. *IEEE TIP*, 2016.
19. J. Hai, Z. Xuan, R. Yang, Y. Hao, F. Zou, F. Lin, and S. Han. R2rnet: Low-light image enhancement via real-low to real-normal network. *JVCI*, 2023.
20. S. W. Hasinoff. Photon, poisson noise. *Computer Vision, A Reference Guide*, 2014.
21. Z. Hu, S. Cho, J. Wang, and M.-H. Yang. Deblurring low-light images with light streaks. In *CVPR*, 2014.
22. Y. Jiang, X. Gong, D. Liu, Y. Cheng, C. Fang, X. Shen, J. Yang, P. Zhou, and Z. Wang. Enlightengan: Deep light enhancement without paired supervision. *IEEE TIP*, 2021.
23. J. Ke, Q. Wang, Y. Wang, P. Milanfar, and F. Yang. Musiq: Multi-scale image quality transformer. In *ICCV*, 2021.
24. L. Kong, J. Dong, J. Ge, M. Li, and J. Pan. Efficient frequency domain-based transformers for high-quality image deblurring. In *CVPR*, 2023.
25. O. Kupyn, T. Martyniuk, J. Wu, and Z. Wang. Deblurgan-v2: Deblurring (orders-of-magnitude) faster and better. In *ICCV*, 2019.
26. E. H. Land. The retinex theory of color vision. *Scientific American*, 1977.
27. B. Li, X. Liu, P. Hu, Z. Wu, J. Lv, and X. Peng. All-in-one image restoration for unknown corruption. In *CVPR*, 2022.
28. C. Li, C.-L. Guo, M. Zhou, Z. Liang, S. Zhou, R. Feng, and C. C. Loy. Embedding fourier for ultra-high-definition low-light image enhancement. *arXiv:2302.11831*, 2023.
29. O. Liba, K. Murthy, Y.-T. Tsai, et al. Handheld mobile photography in very low light. *ACM TOG*, 2019.
30. R. Liu, L. Ma, J. Zhang, X. Fan, and Z. Luo. Retinex-inspired unrolling with cooperative prior architecture search for low-light image enhancement. In *CVPR*, 2021.
31. X. Liu, Z. Wu, A. Li, et al. Ntire 2024 challenge on low light image enhancement: Methods and results. *arXiv:2404.14248*, 2024.
32. W. Luo, Y. Li, R. Urtasun, and R. Zemel. Understanding the effective receptive field in deep convolutional neural networks. In *NeurIPS*, 2016.
33. X. Lv, S. Zhang, C. Wang, Y. Zheng, B. Zhong, C. Li, and L. Nie. Fourier priors-guided diffusion for zero-shot joint low-light enhancement and deblurring. In *CVPR*, 2024.
34. C. Ma, C.-Y. Yang, X. Yang, and M.-H. Yang. Learning a no-reference quality metric for single-image super-resolution. *CVIU*, 2017.
35. L. Ma, T. Ma, R. Liu, X. Fan, and Z. Luo. Toward fast, flexible, and robust low-light image enhancement. In *CVPR*, 2022.
36. A. Mittal, R. Soundararajan, and A. C. Bovik. Making a “completely blind” image quality analyzer. *IEEE SPL*, 2012.
37. S. Nah, T. H. Kim, and K. M. Lee. Deep multi-scale convolutional neural network for dynamic scene deblurring. In *CVPR*, 2017.
38. S. Nah, T. H. Kim, and K. M. Lee. Deep multi-scale convolutional neural network for dynamic scene deblurring. In *CVPR*, 2017.
39. V. Potlapalli, S. W. Zamir, S. Khan, and F. S. Khan. Promptir: Prompting for all-in-one blind image restoration. *arXiv:2306.13090*, 2023.
40. J. Rim, H. Lee, J. Won, and S. Cho. Real-world blur dataset for learning and benchmarking deblurring algorithms. In *ECCV*, 2020.
41. G. Seif and D. Androutsos. Edge-based loss function for single image super-resolution. In *ICASSP*, 2018.
42. A. Shutova, E. Ershov, G. Perevozchikov, et al. Ntire 2023 challenge on night photography rendering. In *CVPRW*, 2023.
43. K. Simonyan and A. Zisserman. Very deep convolutional networks for large-scale image recognition. *arXiv:1409.1556*, 2014.
44. C. Wang, H. Wu, and Z. Jin. Fourllie: Boosting low-light image enhancement by fourier frequency information. In *ACM MM*, 2023.
45. Y. Wang, Y. Yu, W. Yang, L. Guo, L.-P. Chau, A. C. Kot, and B. Wen. Exposurediffusion: Learning to expose for low-light image enhancement. In *ICCV*, 2023.
46. Z. Wang, X. Cun, J. Bao, and J. Liu. Uformer: A general u-shaped transformer for image restoration. In *CVPR*, 2022.
47. C. Wei, W. Wang, W. Yang, and J. Liu. Deep retinex decomposition for low-light enhancement. In *BMVC*, 2018.
48. C. Wei, W. Wang, W. Yang, and J. Liu. Deep retinex decomposition for low-light enhancement. *arXiv:1808.04560*, 2018.
49. J. Whang, M. Delbracio, H. Talebi, C. Saharia, A. G. Dimakis, and P. Milanfar. Deblurring via stochastic refinement. In *CVPR*, 2022.
50. J. Xu, Y. Hou, D. Ren, L. Liu, F. Zhu, M. Yu, H. Wang, and L. Shao. Star: A structure and texture aware retinex model. *IEEE TIP*, 2020.
51. K. Xu, X. Yang, B. Yin, and R. W. Lau. Learning to restore low-light images via decomposition-and-enhancement. In *CVPR*, 2020.
52. X. Xu, R. Wang, C.-W. Fu, and J. Jia. Snr-aware low-light image enhancement. In *CVPR*, 2022.
53. S. Yang, M. Ding, Y. Wu, Z. Li, and J. Zhang. Implicit neural representation for cooperative low-light image enhancement. In *ICCV*, 2023.
54. W. Yang, S. Wang, Y. Fang, Y. Wang, and J. Liu. From fidelity to perceptual quality: A semi-supervised approach for low-light image enhancement. In *CVPR*, 2020.
55. W. Yang, W. Wang, H. Huang, S. Wang, and J. Liu. Sparse gradient regularized deep retinex network for robust low-light image enhancement. *IEEE TIP*, 2021.
56. W. Yu, M. Luo, P. Zhou, C. Si, Y. Zhou, X. Wang, J. Feng, and S. Yan. Metaformer is actually what you need for vision. In *CVPR*, 2022.
57. S. W. Zamir, A. Arora, S. Khan, M. Hayat, F. S. Khan, and M.-H. Yang. Restormer: Efficient transformer for high-resolution image restoration. In *CVPR*, 2022.
58. S. W. Zamir, A. Arora, S. Khan, M. Hayat, F. S. Khan, M.-H. Yang, and L. Shao. Learning enriched features for fast image restoration and enhancement. *IEEE TPAMI*, 2022.
59. J. Zhang, J. Huang, M. Yao, Z. Yang, H. Yu, M. Zhou, and F. Zhao. Ingredient-oriented multi-degradation learning for image restoration. In *CVPR*, 2023.
60. R. Zhang, P. Isola, A. A. Efros, E. Shechtman, and O. Wang. The unreasonable effectiveness of deep features as a perceptual metric. In *CVPR*, 2018.
61. Y. Zhang, X. Guo, J. Ma, W. Liu, and J. Zhang. Beyond brightening low-light images. *IJCV*, 2021.
62. J. Zhao, J. Ma, B. Fang, S. Quan, and F. Hu. Fast motion deblurring using gyroscopes and strong edge prediction. In *ICPR*, 2016.
63. Y. Zhao, Y. Xu, Q. Yan, D. Yang, X. Wang, and L.-M. Po. D2hnet: Joint denoising and deblurring with hierarchical network for robust night image restoration. In *ECCV*, 2022.
64. H. Zhou, W. Dong, X. Liu, S. Liu, X. Min, G. Zhai, and J. Chen. Glare: Low light image enhancement via generative latent feature based codebook retrieval. In *ECCV*, 2025.
65. S. Zhou, C. Li, and C. C. Loy. Lednet: Joint low-light enhancement and deblurring in the dark. In *ECCV*, 2022.
