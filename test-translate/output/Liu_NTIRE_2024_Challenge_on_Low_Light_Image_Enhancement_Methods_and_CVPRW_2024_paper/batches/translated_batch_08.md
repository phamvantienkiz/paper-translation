<<<MATH_TOKEN_0310>>>

trong đó <<<MATH_TOKEN_0311>>> và <<<MATH_TOKEN_0312>>> lần lượt đại diện cho mất mát tái tạo (reconstruction loss), mất mát độ mịn phản xạ (reflectance smoothness loss), và mất mát nhiễu có dẫn đường bởi độ chiếu sáng (illumination-guided noise loss), và <<<MATH_TOKEN_0313>>> đại diện cho các hệ số trọng số tương ứng.

Mạng Khử nhiễu (Denoising network) tạo ra một cặp bản đồ nhiễu [57] từ một ảnh nhiễu đơn lẻ và sử dụng các bản đồ này để huấn luyện một mạng ba tầng đơn giản (CNN kết hợp với kích hoạt SMU [6]). Cụ thể, phương pháp đề xuất bắt đầu bằng việc áp dụng một toán tử lấy mẫu xuống để phân tách đầu ra từ mạng Phân rã thành một cặp ảnh được lấy mẫu xuống. Một trong những quan sát này đóng vai trò là giá trị đầu vào, trong khi ảnh còn lại đóng vai trò là mục tiêu. Phương pháp đề xuất sau đó sử dụng các kỹ thuật chính quy hóa (regularization) trong quá trình huấn luyện để đạt được khả năng khử nhiễu hiệu quả.

Là một phương pháp dành riêng cho một hình ảnh đầu vào duy nhất, nó không yêu cầu bất kỳ mẫu hình ảnh tiên nghiệm hay mô hình huấn luyện trước nào. Kết quả tăng cường cuối cùng có ưu thế về độ sáng và độ tự nhiên của các hình ảnh chiếu sáng không đồng đều.

**Cài đặt thực nghiệm (yanhailong):** Đội thi sử dụng PyTorch và thiết bị kiểm thử là GPU A6000. Nhánh chiếu sáng của mạng Phân rã bao gồm cấu trúc bốn tầng bao gồm Tích chập <<<MATH_TOKEN_0314>>> theo sau bởi các hàm kích hoạt ReLU. Mặt khác, các nhánh phản xạ và nhiễu sử dụng kiến trúc bốn tầng của Tích chập <<<MATH_TOKEN_0315>>> với Denseblock, theo sau bởi các hàm kích hoạt ReLU, đỉnh điểm là một tầng bổ sung của Tích chập <<<MATH_TOKEN_0316>>>. Mạng trải qua tổng cộng 1000 bước lặp trong quá trình huấn luyện. Trong mạng Khử nhiễu, hai tầng Tích chập <<<MATH_TOKEN_0317>>> được sử dụng, mỗi tầng được theo sau bởi kích hoạt SMU, và cuối cùng được kết nối với tầng cuối cùng của Tích chập <<<MATH_TOKEN_0318>>>. Quá trình huấn luyện sử dụng mất mát Sai số Toàn phương Trung bình (MSE) cho 2000 bước lặp. Tất cả các tốc độ học là 0,01; bộ tối ưu hóa sử dụng Adam; không cần huấn luyện trước, đầu vào là một ảnh đơn lẻ sẽ xuất trực tiếp kết quả tăng cường.

### 4.22. Mishka

Hình 22. Sơ đồ minh họa cho thấy ứng dụng của Retinexformer trong tăng cường ảnh thiếu sáng.

**Mô tả:** Như được minh họa trong Hình 22, chúng tôi đã sử dụng mô hình Retinexformer [8], một Transformer dựa trên Retinex một giai đoạn, được thiết kế đặc biệt cho các tác vụ tăng cường ảnh thiếu sáng. Cách tiếp cận của chúng tôi được phân biệt bởi việc huấn luyện mô hình Retinexformer trực tiếp trên tập dữ liệu do ban tổ chức cuộc thi cung cấp, thể hiện khả năng thích ứng và năng lực tổng quát hóa của nó trên các bộ dữ liệu khác nhau. Phương pháp huấn luyện trực tiếp này nhấn mạnh tính hiệu quả và linh hoạt của mô hình đối với các điều kiện thiếu sáng cụ thể. Phương pháp của chúng tôi duy trì mức độ phức tạp vừa phải trong suốt tất cả các giai đoạn, đảm bảo tính hiệu quả từ khâu tiền xử lý dữ liệu đến huấn luyện mô hình và đánh giá cuối cùng.

**Cài đặt thực nghiệm (Mishka):** Cấu hình huấn luyện của chúng tôi trình bày chi tiết các khía cạnh khác nhau của quy trình huấn luyện mô hình. Chúng tôi đã tiến hành tổng cộng 300.000 bước lặp mà không có giai đoạn khởi động (warm-up), và áp dụng cắt tỉa gradient (gradient clipping) để ngăn chặn hiện tượng bùng nổ gradient. Trong quá trình huấn luyện, chúng tôi chia 300.000 bước lặp thành hai chu kỳ:

- Chu kỳ đầu tiên áp dụng tốc độ học cố định là 3e-4 cho 92.000 bước lặp ban đầu.
- Chu kỳ thứ hai áp dụng chiến lược giảm dần cosine, giảm tốc độ học từ <<<MATH_TOKEN_0319>>> xuống <<<MATH_TOKEN_0320>>> qua 208.000 bước lặp tiếp theo.

Chúng tôi cũng sử dụng các kỹ thuật tăng cường dữ liệu hỗn hợp, và đối với cấu hình bộ tối ưu hóa, chúng tôi đã chọn bộ tối ưu hóa Adam với tốc độ học ban đầu là 2e-4 và các hệ số betas được đặt thành [0.9, 0.999]. Về hàm mất mát, chúng tôi đã sử dụng Hàm mất mát <<<MATH_TOKEN_0321>>>, với trọng số mất mát là <<<MATH_TOKEN_0322>>> và phương thức rút gọn (reduction) được đặt thành mean.

## Lời cảm ơn (Acknowledgements)

Công trình này được hỗ trợ một phần bởi Quỹ Humboldt. Chúng tôi xin cảm ơn các nhà tài trợ NTIRE 2024: Meta Reality Labs, OPPO, KuaiShou, Huawei và Đại học Würzburg (Phòng thí nghiệm Thị giác Máy tính).

---

## Phụ lục A: Các Đội thi và Đơn vị Công tác (Appendix A: Teams and Affiliations)

### Ban Tổ chức Thử thách NTIRE 2024 Low Light Enhancement Challenge
**Thành viên:**  
Xiaoning <<<MATH_TOKEN_0323>>> (liuxiaoning2016@sina.com),  
Zongwei Wu$^{2}$<<<MATH_TOKEN_0324>>>,  
Ao Li$^1$ (aoli@std.uestc.edu.cn),  
Florin Vasluianu$^2$ (florin-alexandru.vasluianu@uni-wuerzburg.de),  
Yulun Zhang$^3$ (yulun100@gmail.com),  
Shuhang Gu$^1$ (shuhanggu@gmail.com),  
Le <<<MATH_TOKEN_0326>>> (lezhang<<<MATH_TOKEN_0327>>>uestc.edu.cn),  
Ce Zhu$^1$ (eczhu@uestc.edu.cn),  
Radu Timofte$^{2,4}$<<<MATH_TOKEN_0328>>>  

**Đơn vị công tác:**  
$^1$ Đại học Khoa học và Công nghệ Điện tử Trung Quốc (UESTC), Trung Quốc  
$^2$ Phòng thí nghiệm Thị giác Máy tính, Đại học Würzburg, Đức  
<<<MATH_TOKEN_0330>>> Đại học Giao thông Thượng Hải, Trung Quốc  
$^4$ Phòng thí nghiệm Thị giác Máy tính, ETH Zurich, Thụy Sĩ  

---

### SYSU-FVL-T2
**Tiêu đề:** Tăng cường Ảnh Thiếu sáng Siêu Nét Ổn định theo Tỷ lệ (Scale-Robust Low-light Ultra-High-Definition Image Enhancement)  
**Thành viên:** Zhi Jin$^{1,2}$ (jinzh26@mail.sysu.edu.cn), Hongjun Wu$^1$, Chenxi Wang$^1$, Haitao Ling$^1$  
**Đơn vị:**  
$^1$ Trường Kỹ thuật Hệ thống Thông minh, Đại học Tôn Trung Sơn (Sun Yat-sen University), Thâm Quyến, Quảng Đông, Trung Quốc  
$^2$ Phòng thí nghiệm Trọng điểm Tỉnh Quảng Đông về Khoa học và Công nghệ Phòng cháy Chữa cháy, Quảng Châu, Trung Quốc  

---

### Retinexformer
**Tiêu đề:** Retinexformer: One-stage Retinex-based Transformer for Low-light Image Enhancement  
**Thành viên:** Yuanhao <<<MATH_TOKEN_0331>>> (caiyuanhao1998@gmail.com), Hao <<<MATH_TOKEN_0332>>>, Yuxin Zheng$^2$, Jing Lin$^2$, Alan Yuille$^1$  
**Đơn vị:**  
$^1$ Đại học Johns Hopkins, Hoa Kỳ  
$^2$ Đại học Thanh Hoa, Trung Quốc  

---

### DH-AISP
**Tiêu đề:** Hợp nhất Đặc trưng Đa tỷ lệ cho Tăng cường Ảnh Thiếu sáng  
**Thành viên:** Ben Shao$^1$ (2830802483@qq.com), Jin Guo$^1$, Tianli Liu$^1$, Mohao Wu$^1$  
**Đơn vị:** $^1$ Công ty TNHH Công nghệ Dahua Chiết Giang, Trung Quốc  

---

### NWPU-DiffLight
**Tiêu đề:** DiffLight: Tích hợp Nội dung và Chi tiết cho Tăng cường Ảnh Thiếu sáng  
**Thành viên:** Yixu Feng$^1$ (yixu-nwpu@mail.nwpu.edu.cn), Shuo Hou$^1$, Haotian Lin$^2$, Yu Zhu$^1$, Peng Wu$^1$, Wei Dong$^3$, Jinqiu Sun$^1$, Yanning Zhang$^1$, Qingsen Yan$^1$  
**Đơn vị:**  
$^1$ Khoa Khoa học Máy tính, Đại học Bách khoa Tây Bắc (NWPU), Trung Quốc  
$^2$ Khoa Phần mềm, Đại học Bách khoa Tây Bắc (NWPU), Trung Quốc  
$^3$ Khoa Khoa học Máy tính, Đại học Kiến trúc và Công nghệ Tây An, Trung Quốc  

---

### GiantPandaCV
**Tiêu đề:** UHDMamba: Hướng tới Mô hình Không gian Trạng thái Hiệu quả cho Tăng cường Ảnh Thiếu sáng UHD  
**Thành viên:** Wenbin Zou$^1$ (alexzou14@foxmail.com), Weipeng Yang$^1$, Yunxiang Li$^2$, Qiaomu Wei$^3$, Tian Ye$^4$, Sixiang Chen$^{3,4}$  
**Đơn vị:**  
<<<MATH_TOKEN_0333>>> Đại học Công nghệ Hoa Nam, Trung Quốc  
$^2$ Đại học Phúc Châu, Trung Quốc  
$^3$ Đại học Công nghệ Thông tin Thành Đô, Trung Quốc  
$^4$ Đại học Khoa học và Công nghệ Hồng Kông (Quảng Châu), Trung Quốc  

---

### LVGroup.HFUT
**Tiêu đề:** Khám phá Ứng dụng của NAFNet trong Tăng cường Ảnh Thiếu sáng  
**Thành viên:** Zhao <<<MATH_TOKEN_0334>>> (cszhang@gmail.com), <<<MATH_TOKEN_0335>>> Wang$^1$, Yan Luo$^1$, Zhichao Zuo$^1$, Mingshen Wang$^1$, Junhu Wang$^1$, Yanyan Wei$^1$  
**Đơn vị:** $^1$ Đại học Công nghệ Hợp Phì (HFUT), Trung Quốc  

---

### Try1try8
**Tiêu đề:** Kết hợp Mô hình Tăng cường Thiếu sáng của Đa Mảnh RetinexFormers  
**Thành viên:** Xiaopeng Sun$^1$ (xpsun@stu.xidian.edu.cn), Yu Gao$^1$, Jiancheng Huang$^1$  
**Đơn vị:** $^1$ Nhà nghiên cứu độc lập  

---

### Pixel warrior
**Tiêu đề:** MLP cho Tăng cường Ảnh Thiếu sáng  
**Thành viên:** Hongming Chen$^1$ (chenhongming@stu.sau.edu.cn), Xiang Chen$^2$  
**Đơn vị:**  
$^1$ Đại học Hàng không Vũ trụ Thẩm Dương, Trung Quốc  
$^2$ Đại học Khoa học và Công nghệ Nam Kinh, Trung Quốc  

---

### HuiT
**Tiêu đề:** Phương pháp Tạo ảnh Thiếu sáng Tăng cường Dựa trên Axis-Transformer  
**Thành viên:** Hui Tang$^1$ (2639442956@qq.com), Yuanbin Chen$^1$, Yuanbo Zhou$^1$, Xinwei Dai$^1$, Xintao Qiu$^1$, Wei Deng$^2$, Qinquan <<<MATH_TOKEN_0336>>>, Tong Tong$^{1,2}$  
**Đơn vị:**  
<<<MATH_TOKEN_0337>>> Đại học Phúc Châu, Phúc Châu, Trung Quốc  
<<<MATH_TOKEN_0338>>> Imperial Vision Technology, Phúc Châu, Trung Quốc  

---

### X-LIME
**Tiêu đề:** Ước lượng Đường cong Sâu có Giám sát với Bộ Khử nhiễu  
**Thành viên:** Mingjia Li$^1$ (mingjiali@tju.edu.cn), Jin Hu$^1$, Xinyu He$^1$, Xiaojie Guo$^1$  
**Đơn vị:** $^1$ Đại học Thiên Tân, Trung Quốc  

---

### Image Lab
**Tiêu đề:** Tăng cường Ảnh Thiếu sáng: Phương pháp Tiếp cận Dựa trên SCPA với Kiến trúc RDCA-UNet  
**Thành viên:** Sabarinathan$^1$ (<<<MATH_TOKEN_0339>>>@gmail.com), K Uma$^2$, A Sasithradevi$^3$, B Sathya Bama$^4$, S. Mohamed Mansoor Roomi$^4$, V. Srivatsav$^5$  
**Đơn vị:**  
$^1$ Couger Inc, Nhật Bản  
$^2$ Viện Công nghệ & Kỹ thuật Sasi, Ấn Độ  
$^3$ Viện Công nghệ Vellore, Ấn Độ  
$^4$ Trường Kỹ thuật Thiagarajar, Ấn Độ  
$^5$ Đại học Coventry, Vương quốc Anh  

---

### dgzzqteam
**Tiêu đề:** Khung Làm việc Dựa trên Cổng Một Giai đoạn (One-stage gatebased Framework)  
**Thành viên:** Jinjuan Wang$^1$ (15600951607@163.com), Long Sun$^1$, Qiuying Chen$^1$, Jiahong Shao$^1$, Yizhi Zhang$^1$  
**Đơn vị:** <<<MATH_TOKEN_0341>>> Các nhà nghiên cứu độc lập  

---

### Cidaut AI
**Tiêu đề:** InstructIR: Phục hồi Hình ảnh Chất lượng Cao Tuân theo Chỉ dẫn Con người  
Mã nguồn: https://github.com/mv-lab/InstructIR  
**Thành viên:** Marcos V. Conde$^{1,2}$ (marcos.conde@uni-wuerzburg.de), Daniel Feijoo$^1$, Juan C. Benito$^1$, Alvaro García$^1$  
**Đơn vị:**  
$^1$ Cidaut AI  
$^2$ CVLab, Đại học Würzburg, Đức  

---

### OptDev
**Tiêu đề:** Học Tăng cường Ảnh Thiếu sáng Tối ưu cho các Tác vụ Thị giác Thiết bị Cận biên (Edge Vision)  
**Thành viên:** Jaeho Lee$^1$ (jaeho.lee@opt-ai.kr), Seongwan Kim$^1$, Sharif SMA$^1$, Nodirkhuja Khujaev$^1$, Roman Tsoy$^1$  
**Đơn vị:** $^1$ Opt-AI  

---

### ataza
**Tiêu đề:** Mạng Tăng cường Ảnh Dẫn đường bởi Miền Tần số Hiệu quả cho Tăng cường Ảnh Thiếu sáng và Loại bỏ Bóng đổ  
**Thành viên:** Ali Murtaza$^{1,2}$ (ali.murtaza.ali29@outlook.com), Uswah Khairuddin$^{1,2}$, Ahmad ’Athif Mohd Faudzi$^{1,2}$  
**Đơn vị:**  
$^1$ Viện Công nghệ Quốc tế Malaysia - Nhật Bản (MJIIT), Đại học Công nghệ Malaysia (UTM), Kuala Lumpur, Malaysia  
$^2$ Trung tâm Trí tuệ Nhân tạo và Robot (CAIRO), Đại học Công nghệ Malaysia, Kuala Lumpur, Malaysia  

---

### KLETech-CEVI.LowlightHypnotise
**Tiêu đề:** Hierarchical LightNet: Hướng tới Tăng cường Ảnh Thiếu sáng  
**Thành viên:** Sampada Malagi$^{1,3}$ (sampadamalagi12@gmail.com), Amogh Joshi$^1$, Nikhil Akalwadi$^{1,3}$, Chaitra Desai$^{1,3}$, Ramesh Ashok Tabib$^{1,2}$, Uma Mudenagudi$^{1,2}$  
**Đơn vị:**  
$^1$ Trung tâm Xuất sắc về Trí tuệ Thị giác (CEVI), Đại học Công nghệ KLE, Hubballi, Karnataka, Ấn Độ  
$^2$ Khoa Kỹ thuật Điện tử và Truyền thông, Đại học Công nghệ KLE, Ấn Độ  
$^3$ Khoa Khoa học Máy tính và Kỹ thuật, Đại học Công nghệ KLE, Ấn Độ  

---

### 221B
**Tiêu đề:** Trang bị cho Mô hình Khuếch tán với Entropy Không gian Khả vi cho Tăng cường Ảnh Thiếu sáng  
**Thành viên:** Wenyi <<<MATH_TOKEN_0343>>> (shermanlian<<<MATH_TOKEN_0344>>>163.com), Wenjing <<<MATH_TOKEN_0345>>>  
**Đơn vị:** <<<MATH_TOKEN_0346>>> Đại học Đông Bắc, Trung Quốc  

---

### KLETech-CEVI_Dark Knights
**Tiêu đề:** KnightNet: Mạng Tăng cường Ảnh Thiếu sáng Dẫn đường bởi Độ Chiếu sáng  
**Thành viên:** Jagadeesh <<<MATH_TOKEN_0347>>> (01fe21bcs004<<<MATH_TOKEN_0348>>>), Vijayalaxmi Ashok Aralikatti$^{1,3}$, Palani Yashaswini$^{1,2}$, Nitish Upasi$^1$, Dikshit Hegde$^1$, Ujwala Patil$^{1,2}$, Sujata <<<MATH_TOKEN_0349>>>  
**Đơn vị:**  
$^1$ Trung tâm Xuất sắc về Trí tuệ Thị giác (CEVI), Đại học Công nghệ KLE, Hubballi, Karnataka, Ấn Độ  
$^2$ Khoa Kỹ thuật Điện tử và Truyền thông, Đại học Công nghệ KLE, Ấn Độ  
$^3$ Khoa Khoa học Máy tính và Kỹ thuật, Đại học Công nghệ KLE, Ấn Độ  

---

### BFU-LL
**Tiêu đề:** Mô hình Khuếch tán cho Tăng cường Thiếu sáng  
**Thành viên:** Xingzhuo Yan$^1$ (ayx1sgh@bosch.com), Wei Hao$^2$, Minghan Fu$^3$  
**Đơn vị:**  
<<<MATH_TOKEN_0350>>> Bosch Investment Ltd.  
$^2$ Fortinet, Inc.  
<<<MATH_TOKEN_0351>>> Đại học Saskatchewan  

---

### SVNIT.NTNU
**Tiêu đề:** Tăng cường Ảnh Thiếu sáng Dựa trên Retinex  
**Thành viên:** Pooja Choksy$^1$ (ds22ec003@eced.svnit.ac.in), Anjali Sarvaiya$^1$, Kishor Upla$^1$, Kiran Raja$^2$  
**Đơn vị:**  
$^1$ Viện Công nghệ Quốc gia Sardar Vallabhbhai (SVNIT), Ấn Độ  
$^2$ Đại học Khoa học và Công nghệ Na Uy (NTNU), Na Uy  

---

### yanhailong
**Tiêu đề:** ZSRADNet: Tăng cường Ảnh Thiếu sáng Zero-Shot Retinex Kết hợp Chiếu sáng Thích ứng và Khử nhiễu  
**Thành viên:** Hailong Yan (yhl00825@163.com)  
**Đơn vị:** Đại học Khoa học và Công nghệ Điện tử Trung Quốc (UESTC), Trung Quốc  

---

### Mishka
**Tiêu đề:** Ứng dụng và Thích ứng của Retinexformer  
**Thành viên:** Yunkai Zhang$^1$ (1585832651@qq.com), Baiang Li$^1$, Jingyi Zhang$^1$, Huan Zheng$^2$  
**Đơn vị:**  
$^1$ Đại học Công nghệ Hợp Phì (HFUT), Trung Quốc  
<<<MATH_TOKEN_0352>>> Đại học Ma Cao, Trung Quốc  
