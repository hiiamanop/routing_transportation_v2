# **Sistem Informasi Integrasi Tiga Moda Transportasi Publik Kota Palembang** 

# **(LRT Sumsel, Teman Bus, dan Angkutan Feeder) Berbasis Enhanced DFS dengan Optimasi IDA\* untuk Optimasi Rute** 

## **Melawaty Agustien***<sup>**, 1**</sup> **, Rhaptyalyani Herno Della**<sup>**2**</sup> **, dan Edi Kadarsa**<sup>**3**</sup> 

123Program Studi Teknik Sipil, Universitas Sriwijaya, Jl. Raya Palembang–Prabumulih Km 32, Provinsi Sumatera Selatan 

*E-mail: melawatyagustien@ft.unsri.ac.id 

#### **Abstrak** 

Transportasi umum merupakan salah satu elemen penting dalam mendukung mobilitas perkotaan yang berkelanjutan. Meskipun Kota Palembang telah memiliki berbagai moda transportasi publik seperti LRT Sumsel, Teman Bus, dan angkutan feeder, integrasi informasi antarmoda yang belum optimal masih menjadi tantangan dalam meningkatkan aksesibilitas dan kemudahan perjalanan pengguna. Keterbatasan informasi mengenai perpindahan moda, waktu tempuh perjalanan, dan pemilihan rute yang efisien menyebabkan pemanfaatan transportasi multimoda belum dapat dilakukan secara optimal. Penelitian ini bertujuan untuk mengembangkan sistem informasi integrasi transportasi multimoda yang mampu memberikan rekomendasi rute perjalanan optimal pada jaringan transportasi publik Kota Palembang. Penelitian dilakukan melalui pengumpulan data operasional transportasi menggunakan survei lapangan, GPS tracking, serta pemetaan jaringan transportasi multimoda yang terdiri atas 402 halte dan stasiun, 423 konektivitas antartitik perjalanan, dan 171 titik perpindahan moda transportasi. Sistem memodelkan jaringan transportasi dalam bentuk graf multimoda dan menerapkan algoritma Enhanced Depth First Search (Enhanced DFS) yang dioptimalkan menggunakan Iterative Deepening A* (IDA*) untuk menentukan rute perjalanan optimal berdasarkan beberapa parameter, meliputi waktu tempuh, jarak perjalanan, biaya perjalanan, dan jumlah perpindahan moda. Evaluasi dilakukan menggunakan metrik Mean Absolute Error (MAE), Root Mean Square Error (RMSE), tingkat keberhasilan pencarian rute (success rate), serta waktu respons sistem pada 20 sampel rute nyata (10 skenario sederhana, 10 skenario kompleks) yang dibandingkan terhadap dua baseline (Standard DFS dan conventional routing). Hasil pengujian menunjukkan bahwa Enhanced DFS-IDA* memiliki tingkat keberhasilan pencarian rute yang jauh lebih tinggi dibandingkan kedua baseline (75% berbanding 15% untuk Standard DFS dan 35% untuk conventional routing), namun keunggulan akurasi waktu tempuh (MAE) terhadap kedua baseline tersebut belum dapat dibuktikan signifikan secara statistik pada ukuran sampel yang diuji (paired t-test dan Wilcoxon signed-rank, p>0,05). Sistem yang dikembangkan berhasil mengintegrasikan informasi perjalanan dari tiga moda transportasi publik di Kota Palembang, dengan cakupan ground truth riil (survei lapangan dan jadwal operasional) yang tervalidasi mencapai 75,41% dari total edge jaringan. Penelitian ini diharapkan dapat menjadi salah satu alternatif solusi dalam pengembangan sistem integrasi transportasi publik di kota-kota berkembang di Indonesia, dengan keterbatasan metodologis yang diuraikan secara eksplisit sebagai arah penelitian lanjutan. 

**Kata kunci:** Transportasi multimoda, Enhanced DFS, IDA*, penentuan rute optimal, titik perpindahan moda, Kota Palembang. 

#### **_Abstract_** 

_Public transportation plays an important role in supporting sustainable urban mobility. Although Palembang City has implemented several public transportation modes, including LRT Sumsel, Teman Bus, and feeder services, the lack of integrated multimodal transportation information remains a challenge in improving accessibility and travel convenience for users. Limited information regarding intermodal transfers, travel time estimation, and efficient route selection hinders the optimal utilization of multimodal public transportation services. This study aims to develop a multimodal transportation information system capable of providing optimal travel route recommendations within Palembang City's public transportation network. The study was conducted through transportation operational data collection using field surveys, GPS tracking, and multimodal transportation network mapping consisting of 402 stations and stops, 423 interconnectivity links, and 171 intermodal transfer points. The transportation network is modeled as a multimodal graph and utilizes the Enhanced Depth First Search (Enhanced DFS) algorithm optimized with Iterative Deepening A* (IDA*) to determine optimal travel routes based on multiple criteria, including travel time, travel distance, travel cost, and the number of modal transfers. System performance was evaluated using Mean Absolute Error (MAE), Root Mean Square Error (RMSE), route-finding success rate, and system response time on a sample of 20 real routes (10 simple, 10 complex scenarios) benchmarked against two baselines (Standard DFS and conventional routing). Results show that Enhanced DFS-IDA* achieves a substantially higher route-finding success rate than both baselines (75% versus 15% for Standard DFS and 35% for conventional routing), although its travel-time accuracy (MAE) advantage over the baselines was not statistically significant at the tested sample size (paired t-test and Wilcoxon signed-rank, p>0.05). The developed system successfully integrates travel information from three public transportation modes in Palembang City, with validated real ground-truth coverage reaching 75.41% of network edges. This study contributes to the development of public transportation integration systems for emerging urban areas in Indonesia, with methodological limitations reported explicitly as directions for future work._ 

**_Keywords_ :** _Multimodal transportation, Enhanced DFS, IDA*, optimal route determination, Palembang City._ 

### **1. Pendahuluan** 

Transportasi publik merupakan salah satu komponen penting dalam mendukung mobilitas perkotaan yang berkelanjutan. Pertumbuhan jumlah penduduk dan aktivitas ekonomi di kawasan perkotaan menyebabkan kebutuhan perjalanan masyarakat semakin meningkat sehingga menuntut tersedianya sistem transportasi yang efisien, terintegrasi, dan mudah diakses oleh pengguna. Pengembangan sistem transportasi publik yang terintegrasi tidak hanya berperan dalam mengurangi tingkat kemacetan dan penggunaan kendaraan pribadi, tetapi juga menjadi faktor penting dalam meningkatkan aksesibilitas dan kualitas pelayanan transportasi perkotaan [1]. Seiring dengan perkembangan konsep smart mobility, integrasi berbagai moda transportasi publik melalui pemanfaatan teknologi informasi menjadi salah satu pendekatan yang banyak diterapkan dalam pengembangan sistem transportasi modern [2]. 

Kota Palembang merupakan salah satu kota metropolitan di Indonesia yang telah mengembangkan berbagai moda transportasi publik, seperti Light Rail Transit (LRT) Sumsel, Teman Bus, dan layanan feeder transportasi publik. Kehadiran berbagai moda transportasi tersebut menunjukkan komitmen pemerintah dalam meningkatkan kualitas layanan transportasi publik dan mendorong penggunaan moda transportasi yang lebih berkelanjutan. Namun demikian, keberadaan berbagai moda transportasi publik tersebut belum sepenuhnya didukung oleh sistem informasi perjalanan yang terintegrasi sehingga pengguna masih mengalami kesulitan dalam menentukan rute perjalanan multimoda yang optimal. Permasalahan yang umum ditemui meliputi keterbatasan informasi mengenai titik perpindahan moda transportasi, estimasi waktu tempuh perjalanan, biaya perjalanan, serta alternatif rute yang paling efisien. 

Integrasi transportasi multimoda menjadi salah satu solusi yang banyak diimplementasikan untuk meningkatkan kualitas layanan transportasi publik. Penelitian Kumar dan Khani menunjukkan bahwa integrasi layanan Mobility-on-Demand (MoD) dengan transportasi publik mampu meningkatkan kualitas pelayanan transportasi melalui optimalisasi first-mile dan last-mile, pengurangan tingkat kemacetan, serta peningkatan tingkat pelayanan pengguna transportasi publik [3]. Penelitian tersebut juga menunjukkan bahwa sistem transportasi multimoda yang terintegrasi memiliki potensi untuk meningkatkan penggunaan transportasi publik apabila didukung oleh perencanaan jaringan transportasi yang baik. Selain itu, integrasi layanan multimoda memungkinkan optimalisasi frekuensi operasional moda transportasi dan alokasi sumber daya transportasi secara lebih efisien. 

Di Indonesia, penelitian mengenai integrasi transportasi publik juga menunjukkan pentingnya integrasi antarmoda dalam meningkatkan mobilitas masyarakat perkotaan. Penelitian Margaretha dan Nugroho menunjukkan bahwa implementasi smart mobility di DKI Jakarta melalui integrasi layanan transportasi publik mampu meningkatkan kualitas mobilitas masyarakat dan memberikan kemudahan dalam perpindahan antarmoda transportasi [1]. Penelitian lain yang dilakukan oleh Disy dkk. menunjukkan bahwa MRT Jakarta memiliki peran strategis sebagai simpul utama integrasi transportasi publik melalui integrasi fisik, tarif, serta layanan informasi perjalanan secara real-time dengan moda transportasi lainnya, seperti TransJakarta, KRL Commuter Line, dan LRT Jakarta [2]. Di luar Jakarta, Chairi dkk. meneliti perencanaan integrasi layanan operasional antara railbus dan angkutan umum di Kota Padang berdasarkan waktu tempuh perjalanan, menunjukkan bahwa penjadwalan transfer antarmoda yang belum tersinkronisasi menjadi salah satu hambatan utama integrasi pada kota berkembang berskala menengah [23]. Rahmatullah dkk. juga menemukan bahwa integrasi BRT Trans Semarang dengan Trans Jateng masih menghadapi kendala pada aspek fisik (jarak transfer) dan informasi jadwal, meskipun kedua layanan tersebut secara formal telah terhubung [24]. Hasil-hasil penelitian tersebut menunjukkan bahwa integrasi transportasi publik tidak hanya membutuhkan pembangunan infrastruktur fisik, tetapi juga membutuhkan integrasi informasi perjalanan yang mampu mendukung kemudahan perpindahan antarmoda transportasi, baik di kota metropolitan seperti Jakarta maupun di kota berkembang berskala menengah seperti Padang dan Semarang. 

Meskipun berbagai penelitian terdahulu telah membahas integrasi transportasi publik dan multimoda, sebagian besar penelitian masih berfokus pada aspek kebijakan transportasi, integrasi layanan, serta optimasi desain jaringan transportasi publik. Penelitian Kumar dan Khani berfokus pada optimasi desain jaringan Mobility-on-Demand yang terintegrasi dengan transportasi publik [3], sedangkan penelitian di Indonesia masih didominasi oleh kajian deskriptif-evaluatif terhadap kondisi integrasi yang sudah berjalan, baik di Jakarta [1][2] maupun di kota berkembang seperti Padang [23] dan Semarang [24], tanpa mengembangkan sistem rekomendasi rute berbasis algoritma pencarian pada graf transportasi. Hingga saat ini, penelitian yang mengembangkan sistem informasi integrasi transportasi multimoda berbasis data operasional transportasi aktual untuk menghasilkan rekomendasi rute perjalanan optimal pada kota berkembang di Indonesia masih sangat terbatas. Selain itu, belum ditemukan penelitian yang secara khusus mengintegrasikan berbagai moda transportasi publik di Kota Palembang ke dalam sebuah jaringan transportasi multimoda yang mempertimbangkan waktu tempuh perjalanan, biaya perjalanan, jarak perjalanan, serta perpindahan moda transportasi dalam proses penentuan rute optimal. 

Untuk memperjelas posisi penelitian ini terhadap penelitian terdahulu, Tabel 1 menyajikan perbandingan fitur dan kontribusi penelitian yang telah dilakukan sebelumnya dengan penelitian yang diusulkan. 

2 

**Tabel 1. Research Gap Penelitian** 

|**Parameter**|**Smart Mobility**<br>**Jakarta [1]**|**MRT Jakarta Smart**<br>**Mobility [2]**|**Integrated MoD &**<br>**Transit [3]**|**Penelitian**<br>**Ini**|
|---|---|---|---|---|
|Integrasi multimoda|Ya|Ya|Ya|Ya|
|Sistem informasi<br>perjalanan|Sebagian|Ya|Tidak|Ya|
|Journey Planner|Tidak|Tidak|Tidak|Ya|
|Rekomendasi rute optimal|Tidak|Tidak|Tidak|Ya|
|Transportation graph<br>modelling|Tidak|Tidak|Ya|Ya|
|Multi-objective route<br>optimization|Tidak|Tidak|Ya|Ya|
|Transfer point modelling|Tidak|Tidak|Ya|Ya|
|Data operasional<br>transportasi aktual|Tidak|Sebagian|Ya|Ya|
|Kota berkembang di<br>Indonesia|Tidak|Tidak|Tidak|Ya|
|Kota Palembang|Tidak|Tidak|Tidak|Ya|



Berdasarkan Tabel 1, dapat diketahui bahwa penelitian-penelitian sebelumnya belum mengembangkan sistem informasi integrasi transportasi multimoda yang mampu memberikan rekomendasi rute perjalanan optimal berbasis data operasional transportasi publik aktual pada Kota Palembang. Penelitian ini mengisi kesenjangan tersebut dengan mengembangkan sistem informasi integrasi transportasi multimoda yang mengintegrasikan tiga moda transportasi publik di Kota Palembang ke dalam sebuah graf transportasi multimoda. Sistem yang dikembangkan menggunakan algoritma Enhanced Depth First Search (Enhanced DFS) yang dioptimalkan menggunakan Iterative Deepening A* (IDA*) untuk menentukan rute perjalanan optimal berdasarkan parameter waktu tempuh, biaya perjalanan, jarak perjalanan, dan jumlah perpindahan moda transportasi. 

Penelitian ini bertujuan untuk mengembangkan sistem informasi integrasi transportasi multimoda Kota Palembang yang mampu memberikan rekomendasi rute perjalanan optimal menggunakan pendekatan Enhanced DFS dengan optimasi IDA*. Hasil penelitian diharapkan dapat memberikan kontribusi dalam pengembangan sistem informasi transportasi multimoda pada kota-kota berkembang di Indonesia serta mendukung peningkatan aksesibilitas dan kualitas layanan transportasi publik melalui integrasi informasi perjalanan yang lebih baik. 

### 1.1 Rumusan Masalah 

Berdasarkan uraian latar belakang di atas, rumusan masalah dalam penelitian ini adalah bagaimana mengintegrasikan data operasional beberapa moda transportasi publik di Kota Palembang ke dalam satu jaringan transportasi multimoda berbasis graf, serta bagaimana menghasilkan rekomendasi rute perjalanan optimal dari jaringan tersebut berdasarkan parameter waktu tempuh, biaya perjalanan, jarak perjalanan, dan jumlah perpindahan moda transportasi, mengingat keterbatasan informasi perpindahan antarmoda yang selama ini dialami pengguna transportasi publik di kota tersebut. 

### 1.2 Tujuan Penelitian 

Penelitian ini bertujuan untuk mengembangkan sistem informasi integrasi transportasi multimoda Kota Palembang yang mampu memberikan rekomendasi rute perjalanan optimal menggunakan pendekatan Enhanced DFS dengan optimasi IDA*. Hasil penelitian diharapkan dapat memberikan kontribusi dalam pengembangan sistem informasi transportasi multimoda pada kota-kota berkembang di Indonesia serta mendukung peningkatan aksesibilitas dan kualitas layanan transportasi publik melalui integrasi informasi perjalanan yang lebih baik 

3 

### **2. Metodologi** 

Penelitian ini menggunakan pendekatan Transportation Information System dan Transportation Network Optimization untuk mengembangkan sistem informasi integrasi transportasi multimoda Kota Palembang. Sistem yang diusulkan mengintegrasikan tiga moda transportasi publik, yaitu Light Rail Transit (LRT) Sumatera Selatan, Teman Bus, dan layanan feeder transportasi publik ke dalam sebuah jaringan transportasi multimoda berbasis graf. Penentuan rute perjalanan optimal dilakukan menggunakan algoritma Enhanced Depth First Search (Enhanced DFS) yang dioptimalkan menggunakan Iterative Deepening A* (IDA*) dengan pendekatan multi-objective optimization. 

Metodologi penelitian terdiri atas sembilan tahapan utama, yaitu pengumpulan data transportasi publik, pemodelan jaringan transportasi multimoda, konstruksi graf transportasi, implementasi algoritma Enhanced DFS dan IDA*, optimasi multi-objektif, pengujian terhadap baseline algorithm, perancangan skenario eksperimen, evaluasi performa sistem, serta analisis statistik hasil pengujian. 

### 2.1. Kerengka Penelitian 

|**Judul Penelitian**|<br>Sistem Informasi Integrasi Transportasi Multimoda Kota Palembang<br>Berbasis Algoritma Enhanced DFS|
|---|---|
|**Tujuan Penelitian**|1.<br>Mengidentifikasi dan menganalisis karakteristik perjalanan meliputi rute, jadwal, tarif, serta waktu<br>tempuh angkutan umum konvensional, angkot feeder LRT, Teman Bus, dan LRT di Kota<br>Palembang.<br>2.<br>Mengembangkan sistem informasi transportasi umum terintegrasi berdasarkan informasi titik<br>tujuan, peta, jadwal, biaya perjalanan, estimasi waktu tempuh, dan alternatif rute menggunakan<br>Algoritma DFS.|
|**Kesimpulan**<br>**Analisis**<br>**Pengolahan Data**<br>**Pengumpulan Data**|**Data Primer**<br>1.<br>Data jadwal angkutan umum<br>(angkot, Teman Bus, dan LRT)<br>yang terbaru (_up to date_).<br>2.<br>Data jadwal angkutan umum<br>(angkot, Teman Bus, dan LRT)<br>yang terbaru (_up to date_) dari titik<br>pemberhentian seperti stasiun,<br>halte, dan bus stop angkot feeder<br>LRT.<br>**Data Sekunder**<br>1.<br>Data pemetaan lokasi simpul<br>angkutan transportasi umum.<br>2.<br>Data rute angkutan umum (angkot<br>dan Teman Bus) yang terbaru (_up to_<br>_date_).<br>3.<br>Data tarif angkutan umum (angkot,<br>Teman Bus, dan LRT) yang terbaru<br>(_up to date_).<br>Implementasi sistem informasi transportasi multimoda yang<br>terintegrasi.<br>Sistem informasi transportasi multimoda secara_real time_menyediakan visualisasi peta interaktif<br>menggunakan garis_polyline_berwarna untuk setiap segmen moda transportasi serta informasi detail<br>per segmen meliputi jenis moda, halte, waktu, jarak, dan biaya perjalanan.<br>1.<br>Mengidentifikasi dan menganalisis karakteristik perjalanan angkutan umum.<br>2.<br>Membuat_flowchart_sistem informasi angkutan umum terintegrasi.<br>3.<br>Mengembangkan program dengan Algoritma DFS|



**Gambar 1.** Tahapan penelitian 

Tahapan penelitian yang diusulkan ditunjukkan pada Gambar 1. Tahapan penelitian diawali dengan proses pengumpulan data transportasi publik aktual Kota Palembang yang meliputi data lokasi halte, jadwal operasional, 

4 

tarif perjalanan, titik perpindahan moda transportasi, serta estimasi waktu tempuh perjalanan. Selanjutnya, seluruh data transportasi dimodelkan ke dalam jaringan transportasi multimoda berbasis graf yang menjadi masukan utama bagi algoritma pencarian rute. 

Algoritma Enhanced DFS digunakan untuk melakukan eksplorasi seluruh kemungkinan rute perjalanan yang valid pada jaringan transportasi publik, dipandu oleh heuristik IDA* yang meminimasi waktu tempuh dengan penalti eksplisit untuk perpindahan moda. Fungsi evaluasi berbobot (weighted sum) atas waktu tempuh, biaya perjalanan, jarak perjalanan, dan jumlah perpindahan moda transportasi digunakan sebagai alat analisis untuk membandingkan kandidat rute pada tahap evaluasi hasil (rincian pada subbagian 2.3.2). Terakhir, performa algoritma dievaluasi menggunakan beberapa metrik evaluasi meliputi Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), koefisien determinasi (R²), dan success rate yang dibandingkan dengan baseline algorithm menggunakan analisis statistik. 

### 2.2. Pegumpulan Data 

Kualitas rekomendasi rute perjalanan yang dihasilkan oleh sistem transportasi multimoda sangat dipengaruhi oleh kualitas dan kelengkapan data transportasi publik yang digunakan. Oleh karena itu, penelitian ini menggunakan kombinasi data primer dan data sekunder untuk memperoleh representasi jaringan transportasi publik Kota Palembang yang aktual dan komprehensif. 

Data Primer diperoleh melalui observasi lapangan terhadap layanan transportasi publik Kota Palembang (LRT Sumsel, Teman Bus, dan feeder transportasi publik) menggunakan metode survei dinamis di dalam kendaraan angkutan umum dan Global Positioning System (GPS) tracking. Survei dilakukan selama 30 hari (Oktober 2025) dengan tiga periode harian: pagi (06:00-09:00), siang (12:00-14:00), dan sore (16:00-19:00) untuk menangkap variasi operasional harian. Data yang dikumpulkan mencakup: koordinat halte/stasiun, informasi rute, jadwal operasional aktual, waktu tempuh per segmen, karakteristik transfer moda (jarak transfer, ketersediaan fasilitas), serta struktur tarif angkutan umum. 

Data Sekunder diperoleh dari: (a) jadwal operasional resmi LRT Sumsel dari BPKARSS, (b) data rute Teman Bus dari PT. TMPJ, (c) data rute feeder dari PT. TGM, dan (d) peta dasar jaringan jalan kota Palembang dari Dinas Perhubungan. 

### 2.3. Pengolahan Data 

Tahap awal pengolahan data dilakukan melalui rekapitulasi hasil survei lapangan yang mencakup koordinat halte, informasi rute, jadwal operasional, serta struktur tarif angkutan umum. Pengumpulan data dilakukan menggunakan metode survei dinamis di dalam kendaraan angkutan umum dan _Global Positioning System_ (GPS) tracking. Data hasil survei kemudian diekstraksi dan diolah menjadi basis data transportasi multimoda. Total data yang diperoleh terdiri atas 402 halte dan stasiun dengan 423 ruas jalan konektivitas antarmoda. Data karakteristik angkutan umum yang digunakan dalam sistem meliputi LRT Sumsel, Teman Bus, dan angkutan feeder LRT. Seluruh data tersebut menjadi dasar dalam proses pembentukan jaringan transportasi pada sistem informasi. 

### 2.3.1. Mengidentifikasi dan Menganalisis Karakteristik Data 

Tahap berikutnya adalah pembentukan _network graph_ berbentuk _bidirectional graph_ untuk merepresentasikan konektivitas antar halte dan stasiun. Data input berupa koordinat lokasi halte serta hubungan konektivitas antar rute angkutan umum yang diperoleh dari hasil survei lapangan. Selanjutnya, sistem membangun struktur graph yang terdiri atas _node_ dan _edge_ untuk menggambarkan hubungan antar titik pemberhentian transportasi. Pada penelitian ini, _network graph_ yang dihasilkan terdiri atas 402 _nodes_ dan 423 _edges_ . Struktur graph dua arah ( _bidirectional_ ) memungkinkan sistem melakukan pencarian rute untuk perjalanan pergi maupun kembali secara lebih fleksibel dan efisien. 

### 2.3.2. Membuat Alur Implementasi Sistem Informasi 

Implementasi Sistem Informasi dilakukan dengan menerapkan Algoritma Enhanced DFS yang dikombinasikan dengan optimasi Iterative Deepening A* (IDA*). Enhanced DFS digunakan untuk melakukan eksplorasi jalur (path exploration) pada jaringan transportasi, sedangkan IDA* berfungsi sebagai heuristic guidance dan pruning mechanism untuk membatasi pencarian pada jalur yang lebih potensial menuju rute optimal [11][12]. Fungsi objektif yang dijalankan secara langsung pada proses pencarian ini adalah minimasi waktu tempuh, dengan penalti eksplisit untuk perpindahan moda dan transfer yang tertanam pada bobot setiap edge; fungsi evaluasi berbobot empat-kriteria (weighted sum atas waktu tempuh, biaya perjalanan, jarak perjalanan, dan jumlah perpindahan moda, dengan w₁=0,40; w₂=0,30; w₃=0,15; w₄=0,15) digunakan sebagai alat analisis terpisah untuk membandingkan dan meranking kandidat rute pada tahap evaluasi hasil, bukan sebagai fungsi objektif yang dieksekusi di dalam pencarian IDA* itu sendiri. Pendekatan ini bertujuan untuk meningkatkan efisiensi pencarian rute serta mengurangi kemungkinan eksplorasi jalur yang tidak relevan. Dengan struktur bidirectional graph, sistem dapat melakukan proses traversal jaringan transportasi secara lebih adaptif terhadap berbagai alternatif perjalanan multimoda. Tahapan proses routing menggunakan Enhanced DFS dijelaskan pada Gambar 2. 

5 



<!-- Start of picture text -->
Input Origin & Destination ! ! !<br>| Route Search Request ! ! !<br>! Graph Traversal !<br>|_ Path Data<br>! ! Multi-objective Optimization !<br>! ! Optimal Route ! |<br>! Route with Details ! ! !<br>Visualized Route & Information ! ! !<br>' ' ' ' '<br><!-- End of picture text -->

Terhadap kombinasi bobot dasar (w₁=0,40 untuk waktu tempuh; w₂=0,30 untuk biaya; w₃=0,15 untuk jarak; w₄=0,15 untuk jumlah perpindahan moda), dilakukan analisis sensitivitas dengan menggeser nilai bobot waktu tempuh (w₁) pada rentang ±0,10 dari nilai dasar, sambil menyesuaikan proporsi bobot parameter lainnya agar totalnya tetap 1. Analisis dilakukan dengan menghitung ulang skor fungsi evaluasi berbobot pada kandidat rute riil (hasil keluaran ketiga algoritma pada studi kasus rute kompleks, subbagian 3.2) menggunakan normalisasi min-max antar kandidat. Hasil analisis menunjukkan bahwa pergeseran w₁ sebesar ±0,10 menghasilkan pergeseran nilai skor fungsi evaluasi hingga 25% pada kandidat rute yang diuji, jauh lebih besar dari perkiraan awal (<8%) yang sebelumnya dilaporkan tanpa perhitungan eksplisit. Peringkat rute terbaik pada kasus yang diuji tidak berubah pada rentang pergeseran tersebut, namun besarnya pergeseran skor mengindikasikan bahwa kombinasi bobot ini tidak dapat diklaim robust tanpa pengujian pada jumlah kandidat dan skenario yang jauh lebih besar. Penelitian lanjutan dengan survei preferensi pengguna (stated preference) atau Analytic Hierarchy Process (AHP) tetap diperlukan untuk memperkuat validitas pembobotan secara statistik dan menggantikan penentuan bobot heuristik yang digunakan saat ini. 

### 2.4 Baseline Pembanding dan Skema Evaluasi 

Untuk mengukur kontribusi mekanisme heuristic guidance dan pruning berbasis IDA* pada Enhanced DFS, performa sistem dibandingkan terhadap dua baseline, yaitu Standard DFS dan conventional routing. 

Standard DFS merupakan implementasi algoritma Depth First Search dasar pada graf transportasi multimoda yang sama (G = (V, E), |V| = 402, |E| = 423), menggunakan opsi pergerakan yang identik dengan Enhanced DFS (edge langsung dan opsi perpindahan moda dalam radius 0,6 km), tetapi tanpa fungsi evaluasi heuristik h(n) dan tanpa mekanisme iterative deepening/pruning berbasis ambang batas f(n) sebagaimana diterapkan pada Enhanced DFS (Persamaan 1). Standard DFS menelusuri cabang graf dengan backtracking hingga kedalaman maksimum 15 tanpa urutan/pemangkasan berbasis heuristik, sehingga digunakan sebagai baseline untuk mengisolasi kontribusi murni komponen IDA* terhadap akurasi dan efisiensi pencarian rute. 

Conventional routing diimplementasikan sebagai algoritma greedy naif: pada setiap simpul, sistem memilih tetangga (edge langsung atau opsi perpindahan moda terdekat) yang secara garis lurus (haversine) paling dekat dengan simpul tujuan, tanpa mempertimbangkan biaya, waktu tempuh riil, atau jumlah perpindahan moda, dan tanpa backtracking maupun lookahead. Pendekatan ini merepresentasikan strategi routing tunggal-objektif dan tidak terstruktur yang umum pada sistem informasi transportasi konvensional yang belum menerapkan optimasi multi-kriteria maupun pencarian sistematis. 

Ground truth. Waktu tempuh referensi (ground truth) yang digunakan untuk perhitungan MAE dan RMSE diperoleh dari data operasional riil yang telah dikumpulkan pada tahap survei lapangan: (1) log perjalanan 30 hari per-segmen untuk 8 koridor Angkot Feeder dan 2 koridor Teman Bus, yang dirata-ratakan per pasangan halte untuk memperoleh waktu tempuh riil per segmen, dan (2) jadwal operasional LRT Sumsel, yang waktu antar stasiunnya diturunkan dari selisih jadwal keberangkatan terjadwal pada kedua arah perjalanan. Kombinasi kedua sumber ini, setelah verifikasi ulang terhadap penamaan koridor pada kode program, mencakup 319 dari 423 edge pada graf (75,41%). Edge yang tidak tercakup (104 edge) terdiri atas: 75 edge pada Teman Bus Koridor 5 (survei 30 hari untuk koridor ini hanya mencakup 22 dari 97 halte lokal pada rute tersebut, bukan keseluruhan rute), 20 edge pada Feeder Koridor 5 (graf merepresentasikan edge dua arah sementara survei hanya mencatat satu arah perjalanan), 5 edge pada LRT Sumsel (edge yang melompati beberapa stasiun sehingga tidak dapat dipetakan langsung ke selisih jadwal antar-stasiun bertetangga), serta 4 edge pada Feeder Koridor 7 dan 8 yang berada di luar rentang halte yang tersurvei. Edge yang tidak tercakup menggunakan estimasi formula waktu-jalan-kaki/formula jarak yang sudah diterapkan secara konsisten pada seluruh sistem. Ground truth dihitung per jalur yang diusulkan oleh masing-masing algoritma (bukan satu referensi bersama), dengan menjumlahkan waktu tempuh riil untuk setiap segmen pada jalur tersebut, sehingga MAE/RMSE mengukur seberapa akurat estimasi waktu setiap algoritma terhadap kondisi operasional riil untuk rute yang benar-benar diusulkannya. 

Uji signifikansi statistik. Pengujian dilakukan pada 20 pasangan asal-tujuan riil (10 skenario sederhana dengan jarak lurus 1,5–5 km, 10 skenario kompleks dengan jarak lurus 8–16 km), disampel dari halte-halte pada jaringan yang sama. Error absolut (|waktu prediksi − ground truth|) dihitung untuk setiap rute yang berhasil ditemukan oleh masing-masing algoritma. Normalitas distribusi error per algoritma diuji dengan uji Shapiro-Wilk (α=0,05). Perbandingan berpasangan antara Enhanced DFS-IDA* dan tiap baseline dilakukan hanya pada subset skenario yang berhasil ditemukan oleh **kedua** algoritma yang dibandingkan (pairwise-complete), menggunakan paired t-test apabila kedua distribusi error normal, atau uji Wilcoxon signed-rank apabila salah satu/kedua distribusi tidak normal. Hasil lengkap (n, statistik uji, derajat bebas jika berlaku, dan p-value) disajikan pada subbagian 3.1.

### **3. Hasil dan Pembahasan** 

Hasil dan pembahasan berisi hasil analisis dan evaluasi terhadap data interpretasi hasil analisis dan bahasan untuk memperoleh jawaban, nilai tambah dan kemanfaatan terkait dengan permasalahan dan tujuan penelitian. Hasil analisis harus menjawab permasalahan dan tujuan penelitian. 

### 3.1. Hasil Implementasi Enhanced DFS 

Untuk mempermudah proses pengamatan dan interpretasi hasil, implementasi algoritma _Enhanced Depth First Search_ (Enhanced DFS) dengan optimasi IDA* pada sistem informasi transportasi multimoda dibandingkan dengan Standard DFS dan _conventional routing_ pada sampel 20 rute nyata (10 skenario sederhana dengan jarak lurus origin-destination 1,5–5 km, dan 10 skenario kompleks dengan jarak lurus 8–16 km), menggunakan pasangan halte asal-tujuan riil dari jaringan transportasi yang sama (G = (V, E), |V| = 402, |E| = 423). Ground truth per rute dihitung mengikuti metodologi pada subbagian 2.4, dengan cakupan riil 75,41% sebagaimana diuraikan pada subbagian tersebut. Hasil pengujian disajikan pada Tabel 2. 

**<u>Tabel 2.</u>** <u>Hasil pengujian pada sampel 20 rute nyata (n=jumlah rute yang berhasil ditemukan pada kategori tersebut)</u> 

|**Algorithm**|**Skenario**|**n**|**MAE (min)**|**RMSE (min)**|**R²**|**Success Rate**|
|---|---|---|---|---|---|---|
|Enhanced DFS-IDA*|Simple Routes|9/10|8.308728|13.642955|0.550691|90%|
|Enhanced DFS-IDA*|Complex Routes|6/10|4.876648|5.324960|0.897549|60%|
|Enhanced DFS-IDA*|**Overall**|**15/20**|**6.935896**|**11.091448**|**0.713467**|**75%**|
|Standard DFS|Simple Routes|3/10|6.276866|7.101199|0.892532|30%|
|Standard DFS|Complex Routes|0/10|-|-|-|0%|
|Standard DFS|**Overall**|**3/20**|**6.276866**|**7.101199**|**0.892532**|**15%**|
|Conventional|Simple Routes|4/10|12.920196|19.602703|0.495315|40%|
|Conventional|Complex Routes|3/10|8.383501|13.329539|-0.049543|30%|
|Conventional|**Overall**|**7/20**|**10.975898**|**17.196734**|**0.802257**|**35%**|

Berdasarkan Tabel 2, temuan paling menonjol adalah pada _success rate_: Enhanced DFS-IDA* jauh lebih andal dalam menemukan rute sama sekali (75% dari 20 skenario) dibandingkan Standard DFS (15%) dan _conventional routing_ (35%). Selisih ini konsisten dengan peran mekanisme _heuristic guidance_ dan _iterative deepening_ IDA* dalam mengurangi kegagalan pencarian pada jalur yang membutuhkan banyak simpul perantara, mengingat Standard DFS dibatasi kedalaman maksimum 15 tanpa panduan heuristik dan gagal menemukan rute sama sekali pada seluruh 10 skenario kompleks yang diuji. 

Sebaliknya, pada metrik akurasi waktu tempuh (MAE/RMSE), hasil pengujian **tidak mendukung klaim bahwa Enhanced DFS-IDA* secara konsisten lebih akurat** dibandingkan kedua baseline. Pada skenario sederhana, MAE Enhanced DFS-IDA* (8,308728 menit) justru lebih tinggi daripada MAE Standard DFS (6,276866 menit) untuk tiga rute yang sama-sama berhasil ditemukan kedua algoritma. Uji signifikansi berpasangan mengikuti prosedur pada subbagian 2.4 mengonfirmasi bahwa selisih ini tidak signifikan secara statistik (paired t-test, t=-0,888368, df=2, p=0,468071). Perbandingan Enhanced DFS-IDA* terhadap _conventional routing_ pada 7 rute yang berhasil ditemukan kedua algoritma juga tidak signifikan (uji Wilcoxon signed-rank, W=9,0, p=0,843750). Nilai R² conventional routing pada skenario kompleks bahkan negatif (-0,049543), mengindikasikan performa prediksi yang lebih buruk dari sekadar memprediksi rata-rata pada sub-sampel kecil (n=3) tersebut. 

Dengan demikian, kontribusi IDA* pada Enhanced DFS yang dapat dibuktikan secara empiris pada pengujian ini adalah **peningkatan keandalan pencarian rute (success rate)**, bukan **keunggulan akurasi waktu tempuh yang signifikan secara statistik**. Interpretasi ini berbeda dari versi awal naskah, yang mengklaim keunggulan pada kedua aspek tanpa menyertakan uji signifikansi maupun rincian ukuran sampel. Perbedaan MAE yang tampak pada Tabel 2 kemungkinan besar dipengaruhi oleh ukuran sampel berpasangan yang kecil (n=3 dan n=7) sebagai konsekuensi dari rendahnya _success rate_ Standard DFS dan _conventional routing_; pengujian pada jumlah skenario yang jauh lebih besar diperlukan untuk menyimpulkan ada-tidaknya keunggulan akurasi secara meyakinkan. 

Penelitian ini belum melakukan pembandingan langsung antara Enhanced DFS dengan algoritma routing modern lain yang umum digunakan pada sistem transit multimoda, seperti RAPTOR [21] atau Connection Scan Algorithm (CSA) [22], karena kedua algoritma tersebut dirancang untuk jaringan dengan struktur jadwal yang baku, sementara sebagian rute angkutan umum di Kota Palembang masih bersifat semi-formal tanpa jadwal tetap yang dipublikasikan. Pembandingan langsung dengan algoritma tersebut tetap merupakan arah penelitian lanjutan yang relevan, khususnya apabila ketersediaan data jadwal angkutan umum di Kota Palembang semakin terstandardisasi pada masa mendatang. 

Secara keseluruhan, hasil penelitian ini menunjukkan bahwa penerapan Enhanced DFS memiliki implikasi yang signifikan dalam pengembangan sistem transportasi multimoda, terutama pada aspek keandalan penemuan rute pada jaringan yang kompleks. Dengan demikian, Enhanced DFS dapat menjadi salah satu alternatif pendekatan yang efektif dalam pengembangan _intelligent transportation system_ berbasis integrasi operasional transportasi multimoda di Kota Palembang, dengan catatan bahwa klaim keunggulan akurasi waktu tempuh memerlukan validasi lebih lanjut pada sampel yang lebih besar. 

### 3.2. Pengujian Skenario Rute Kompleks 

Pengujian skenario rute kompleks dilakukan untuk mengevaluasi kemampuan sistem informasi integrasi transportasi multimoda berbasis algoritma _Enhanced Depth First Search_ (Enhanced DFS) dalam menentukan rute optimal pada kondisi perjalanan yang melibatkan beberapa perpindahan moda transportasi. Skenario pengujian dilakukan pada perjalanan dengan titik asal Perumnas OPI Jakabaring yang memiliki koordinat (-3.0438, 104.7861) menuju Universitas Sriwijaya Kampus Palembang dengan koordinat (-2.98525, 104.732880). Jarak perjalanan pada skenario ini adalah sekitar 12,75 km. Pemilihan rute tersebut didasarkan pada karakteristik perjalanan yang melibatkan tiga moda transportasi sekaligus (Feeder Koridor 4, LRT Sumsel, dan Feeder Koridor 7) dalam satu perjalanan, sehingga representatif untuk menguji kemampuan sistem menangani perpindahan multimoda pada rute yang kompleks. 

Validasi terhadap ground truth. Rute yang dihasilkan sistem terdiri atas 22 segmen dengan estimasi waktu tempuh total 56,86650973326238 menit. Untuk menjawab keterbatasan yang teridentifikasi pada versi naskah sebelumnya (estimasi rute tunggal ini belum pernah dibandingkan terhadap data pengukuran riil), setiap segmen dicocokkan terhadap sumber ground truth pada subbagian 2.4: 17 dari 22 segmen (77,27%) memiliki ground truth riil (13 segmen Feeder Koridor 4/7 bersumber survei 30 hari, 4 segmen LRT Sumsel bersumber jadwal operasional), sedangkan 5 segmen sisanya (2 segmen jalan kaki, 3 segmen perpindahan moda) menggunakan estimasi formula sebagaimana didefinisikan pada seluruh sistem. Waktu tempuh teranchor-data — hasil penjumlahan waktu ground truth riil untuk segmen yang tercakup dan estimasi formula untuk segmen yang tidak tercakup — adalah 58,754728 menit, berbeda 1,888219 menit (3,32%) dari estimasi sistem. Selisih sebesar ini berada dalam rentang yang wajar untuk estimasi rute multimoda, namun tetap menunjukkan bahwa validasi lapangan langsung terhadap waktu tempuh aktual pada rute spesifik ini (bukan hanya terhadap data survei per-segmen yang telah diagregasi) masih diperlukan untuk memperkuat klaim akurasi, khususnya karena studi kasus ini tetap merupakan contoh tunggal (_single case_) dan belum mewakili variasi kondisi rute kompleks lainnya. 

8 



<!-- Start of picture text -->
aiaenhanced_dfs_result  COMERROMGIONIAGOSTGEIONG) — [Savelitimemmwalking distance 190mSeminotes||_| OPIWalk Jakabaring 480m to Fee tp<br>2 jroute|total_costsequenceMagen os| +.---»{Transferto LRT Sumsel<br>laccuracy _—_—«[R®——[Rp 5,000= 0.91 TransferLRT Sumselto Feeder ~ Stasiun Koridor Bumi 7 Sriwijaya<br>Feeder Koridor 7 > UNSRI<br><!-- End of picture text -->



<!-- Start of picture text -->
® Palembang Public Transport Routing FF Route (Optimized<br>Find optimal routes using Dijkstra and DFS algorithms © PerumnasOP! JakaboringDFS)—» Feeder Koridor 4 -<br>©© FeederFeder Korior4-Kordor 4 - HateHake 76 --«FeederFeeder KordorKoridor 4 4-H- +.<br>4 Feader (St<br>* Plan Your Route / +me PAit A Pune gfxXa SeiSeapee 8+ ©©——@© Stasiun StasiunKorotFeoder Koridor4LRTLRTFeeder PasarPoteste 4 -(StaHalte16 Poesta—te Stasum 8 Koridor~+ Stasiun - PerumLRT Pasar 16OPI)  tirSt<br>boPerumnas OPI Jakabaring ,\ eer Oe eeER VJP ©©Seca recrencneStasiunStasiunLRTLRT DistPasar Cinde—- Stasiun—StasiuneuimrcamoneLRT BumLRTLRT Pasar DishaSrevjayaCi<br>¥ em © BS LRT bur srmwtjayaada - BS Oped suse!<br>-3.0438 2 104.7861 é , § 20 We w ESE= = © BS Dprt sume acta —- BS arya dt ac ada<br>Destination%UniversitasUse current Sriwijayalocaton om rine|1i}a1rk| geePOalin} .eras PeYeepuemuyZ “allNobostaga. "feeoaNyabeart~~\ Tenggeconeath tanat } 7) ©© © ©©#88 BS BSBS8SBSemporium ary Famty smanpuncak20nlau Aad 22duta2  Asda daskuning a da a adadaBS— —~ —- BS rouBS BS A nda emporium+ BSsanBS son kamengpuncak A.oda 22~2 aaBSada sihuningada Famaymani AAsda adaA ade<br>: a: pO eet ltl 4 orn Reva sel =dosnt<br><—a ~ Kemeng Mont /| >t" Se C oelore a ©(© BS1 padang simpang setasapolsek—-adaRiemart —- H. padangDemang selasaLebar Daun<br>DFS + | 7=wy ee ‘ e | + FF urey<br>Departure Time ‘\ “=o . hae _t\ ;\<br>06/11/2025, 03.43 » 7 os ; i<br>er \ f<br>Ne ate , . oF i l eataditt| © Conareenne exatedion<br>= tne<br>_ ne if Route Summary (Optimized DFS)<br>© Total Time: 56m<br><!-- End of picture text -->

10 

### **4. Kesimpulan** 

Penelitian ini telah berhasil mengembangkan dan mengimplementasikan sistem informasi integrasi transportasi multimoda Kota Palembang berbasis algoritma Enhanced DFS dengan optimasi IDA* yang mengintegrasikan tiga moda transportasi publik utama (LRT Sumsel, Teman Bus, dan angkutan feeder LRT) ke dalam satu jaringan graf multimoda komprehensif. Sistem yang dikembangkan berhasil mengintegrasikan data operasional dari 402 halte dan stasiun, 423 konektivitas antarmoda, dan 171 titik transfer ke dalam basis data jaringan yang terstruktur berdasarkan survei lapangan intensif selama 30 hari dan GPS tracking yang menangkap kondisi operasional sesungguhnya, dengan cakupan ground truth riil yang tervalidasi mencapai 75,41% dari total edge jaringan. Pengujian pada sampel 20 rute nyata (10 skenario sederhana, 10 skenario kompleks) menunjukkan bahwa keunggulan utama Enhanced DFS-IDA* yang dapat dibuktikan secara empiris adalah pada **keandalan penemuan rute** (_success rate_ 75%, dibandingkan 15% pada Standard DFS dan 35% pada _conventional routing_), yang secara langsung dapat diatribusikan pada mekanisme _heuristic guidance_ dan _iterative deepening_ IDA* dalam menghindari kebuntuan pencarian pada jaringan yang kompleks. Pada metrik akurasi waktu tempuh (MAE/RMSE), pengujian belum dapat membuktikan keunggulan Enhanced DFS-IDA* secara signifikan secara statistik dibandingkan kedua baseline pada ukuran sampel yang diuji (paired t-test terhadap Standard DFS: p=0,468071; uji Wilcoxon signed-rank terhadap _conventional routing_: p=0,843750); klaim keunggulan akurasi pada versi naskah sebelumnya tidak dapat direplikasi dan telah dikoreksi. Fungsi evaluasi berbobot empat-kriteria (weighted sum, w₁=0,40; w₂=0,30; w₃=0,15; w₄=0,15) digunakan sebagai alat analisis untuk membandingkan kandidat rute, bukan sebagai fungsi objektif yang berjalan pada proses pencarian rute produksi (yang berbasis minimasi waktu tempuh); bobot ini ditentukan secara heuristik dan belum melalui proses kalibrasi formal maupun survei preferensi pengguna. Sehubungan dengan permasalahan awal penelitian ini — rendahnya pangsa penggunaan angkutan umum di Kota Palembang (4,9%) akibat, salah satunya, keterbatasan informasi perpindahan antarmoda — peningkatan keandalan penemuan rute pada sistem ini berpotensi mengurangi salah satu hambatan tersebut, meskipun penelitian ini belum mengukur dampaknya secara langsung terhadap perubahan pangsa moda dan memerlukan kajian lanjutan (misalnya survei preferensi pengguna pasca-implementasi) untuk memvalidasi keterkaitan ini secara empiris. 

Secara teknis, hasil penelitian ini memberikan kontribusi penting dalam pengembangan sistem transportasi cerdas (intelligent transportation system), khususnya pada wilayah perkotaan seperti Kota Palembang yang memiliki karakteristik jaringan transportasi multimoda yang kompleks. Penggunaan Enhanced DFS memungkinkan proses pencarian rute dilakukan secara lebih efisien tanpa memerlukan tingkat computational complexity yang tinggi sebagaimana beberapa algoritma optimasi lainnya. Kondisi ini berpotensi mengurangi kebutuhan sumber daya sistem (resource requirement) serta meningkatkan efisiensi proses komputasi pada sistem informasi transportasi. Selain itu, penerapan pendekatan optimasi berbasis heuristic melalui IDA* mampu meningkatkan kemampuan sistem dalam menentukan rute optimal pada kondisi jaringan transportasi yang dinamis dan heterogen. 

Secara praktis, temuan ini dapat ditindaklanjuti oleh pemangku kepentingan transportasi Kota Palembang. Dinas Perhubungan Kota Palembang dapat memanfaatkan pemetaan titik perpindahan moda dan estimasi waktu tempuh yang dihasilkan sistem sebagai bahan evaluasi kinerja jaringan transportasi publik serta perencanaan penambahan titik transfer strategis. Bagi operator moda transportasi, seperti Balai Pengelola Kereta Api Ringan Sumatera Selatan (BPKARSS) untuk LRT Sumsel dan PT. Trans Musi Palembang Jaya (PT. TMPJ) untuk Teman Bus, data waktu tempuh dan pola perpindahan moda yang dihasilkan sistem berpotensi menjadi masukan dalam penyesuaian jadwal operasional dan alokasi armada pada titik-titik dengan volume perpindahan tinggi. 

### 4.1 Keterbatasan Penelitian 

Penelitian ini masih memiliki sejumlah keterbatasan yang perlu menjadi perhatian dalam interpretasi temuan maupun arah pengembangan lanjutan. 

Pertama, cakupan sistem informasi yang dikembangkan baru mengintegrasikan tiga dari lima moda transportasi publik yang teridentifikasi di Kota Palembang, yaitu LRT Sumsel, Teman Bus, dan angkutan feeder LRT, sementara angkutan kota konvensional dan angkutan sungai belum tercakup dalam jaringan transportasi multimoda yang dimodelkan. 

Kedua, nilai bobot pada fungsi objektif weighted sum (w₁=0,40; w₂=0,30; w₃=0,15; w₄=0,15) ditentukan secara heuristik berdasarkan hasil observasi lapangan dan belum melalui proses kalibrasi formal seperti Analytic Hierarchy Process (AHP) atau survei preferensi pengguna (stated preference); tidak terdapat survei preferensi pengguna yang mendasari nilai bobot ini. Analisis sensitivitas terhadap pergeseran w₁ (±0,10) pada rute kandidat riil menunjukkan pergeseran skor fungsi evaluasi hingga 25%, jauh lebih besar dari perkiraan sebelumnya (<8%) yang dilaporkan tanpa perhitungan eksplisit — kombinasi bobot ini **tidak dapat diklaim robust** dan validasi lebih lanjut terhadap preferensi pengguna riil sangat diperlukan. Perlu ditegaskan pula bahwa fungsi weighted sum ini berperan sebagai alat evaluasi analitis untuk membandingkan kandidat rute, bukan sebagai fungsi objektif yang dijalankan pada proses pencarian rute produksi (yang berbasis minimasi waktu tempuh dengan penalti transfer). 

Ketiga, ground truth waktu tempuh riil yang digunakan pada bagian 3.1 (data survei operasional 30 hari dan jadwal LRT) mencakup 319 dari 423 edge pada graf (75,41%). Edge yang tidak tercakup (104 edge) sebagian besar disebabkan oleh cakupan survei yang tidak menjangkau seluruh rute (Teman Bus Koridor 5, Feeder Koridor 5) dan edge LRT non-adjacent yang tidak dapat dipetakan ke jadwal antar-stasiun bertetangga (rincian pada subbagian 2.4), bukan semata-mata karena edge tersebut adalah edge jalan kaki/perpindahan moda seperti yang dinyatakan pada versi naskah sebelumnya. Perluasan cakupan survei operasional ke seluruh rute, termasuk validasi waktu jalan kaki riil di titik-titik transfer, tetap diperlukan untuk memperkuat validitas ground truth secara menyeluruh. 

Keempat, pengujian performa pada sampel 20 rute nyata menunjukkan _success rate_ Enhanced DFS-IDA* sebesar 75%, Standard DFS 15%, dan _conventional routing_ 35% — jauh di bawah 100%/87%/78% yang dilaporkan pada versi naskah sebelumnya, yang ternyata berbasis satu rute per kategori per algoritma (n=1) tanpa uji signifikansi. Ukuran sampel berpasangan yang tersedia untuk uji signifikansi (n=3 untuk perbandingan terhadap Standard DFS, n=7 terhadap _conventional routing_) juga relatif kecil sebagai konsekuensi rendahnya _success rate_ kedua baseline tersebut, sehingga hasil uji non-signifikan pada penelitian ini (p=0,468071 dan p=0,843750) belum dapat disimpulkan sebagai bukti tidak adanya perbedaan akurasi, melainkan indikasi bahwa pengujian pada jumlah skenario yang jauh lebih besar diperlukan untuk kesimpulan yang meyakinkan. 

11 

### 4.2 Pengembangan Lebih Lanjut 

Untuk pengembangan lebih lanjut, penelitian selanjutnya disarankan berfokus pada penanganan keterbatasan yang telah diidentifikasi pada bagian 4.1. Pertama, cakupan sistem perlu diperluas dengan mengintegrasikan angkutan kota konvensional dan angkutan sungai ke dalam graf transportasi multimoda. Kedua, penentuan bobot pada fungsi objektif disarankan menggunakan metode formal seperti Analytic Hierarchy Process (AHP) atau survei preferensi pengguna (stated preference) untuk memperkuat validitas hasil optimasi, mengingat analisis sensitivitas pada penelitian ini menunjukkan bobot heuristik saat ini belum robust (pergeseran skor hingga 25% untuk pergeseran bobot ±0,10). Ketiga, pengujian performa algoritma perlu dilakukan pada jumlah dan variasi skenario yang jauh lebih besar daripada 20 rute yang diuji pada penelitian ini, khususnya untuk memperoleh ukuran sampel berpasangan yang memadai bagi uji signifikansi statistik pada metrik akurasi (MAE/RMSE), disertai validasi lapangan langsung, termasuk untuk studi kasus rute kompleks. Selain fokus pada penganan keterbatasan terdapat hal yang dapat dikembangkan lagi, diantaranya: integrasi sistem secara real time menggunakan teknologi GPS tracking dan pengolahan data lalu lintas dinamis dapat diterapkan agar estimasi waktu tempuh lebih responsif terhadap kondisi actual, pengembangan sistem ke dalam platform aplikasi bergerak (mobile application) serta penerapan cloudbased scalability juga diperlukan agar sistem mampu mengakomodasi jaringan transportasi yang lebih luas dan jumlah pengguna yang lebih besar. Dengan pengembangan tersebut, Enhanced DFS yang telah dioptimasi berpotensi menjadi dasar dalam pengembangan sistem transportasi cerdas yang adaptif terhadap perubahan kondisi lalu lintas, pola perjalanan pengguna, dan dinamika operasional transportasi perkotaan. Dampak lain yang bisa diperoleh dari pengembangan sistem ini adalah, apabila sistem ini dapat dikombinasikan dengan integrasi realtime, aplikasi mobile yang user-friendly dan mudah diakses, serta kampanye promosi terpadu untuk meningkatkan awareness masyarakat untuk menggunakan transportasi umum 

### **Ucapan Terima Kasih** 

Penulis mengucapkan terima kasih kepada LPPM Universitas Sriwijaya, Dinas Perhubungan Kota Palembang, Balai Pengelola Kereta Api Ringan Sumatera Selatan (BPKARSS), PT. Trans Musi Palembang Jaya (PT. TMPJ) dan PT. Transportasi Global Mandiri (PT.TGM) yang telah membantu menyediakan data operasional, akses survey lapangan, dan dukungan teknis. Penulis sangat mengapresiasi dukungan dari Program Studi Teknik Sipil Universitas Sriwijaya dan mahasiswa yang terlibat dalam pengumpulan data. 

### **Daftar Pustaka** 

- [1] Margaretha, A., & Nugroho. "Transportasi Publik Terintegrasi: Optimalisasi Implementasi Smart Mobility di DKI Jakarta", 2023. 

- [2] Disy, C. D. A., et al. "Implementasi Kebijakan MRT Jakarta terhadap Pengembangan Integrasi Transportasi Publik Berbasis Smart Mobility di DKI Jakarta", 2026. 

- [3] Kumar, P., & Khani, A. "Planning of Integrated Mobility-on-Demand and Urban Transit Networks", Transportation Research Part A, 2022. 

- [4] M. Agustien, M. Rizki, A. L. Yuono, M. Agustini, dan I. Satriadi, “Spatial Characteristics Visualization of Transfer Point Infrastructure,” _Journal of Advanced Research in Applied Sciences and Engineering Technology_ , vol. 62, no. 2, hlm. 1–14, Nov 2024, doi: 10.37934/araset.64.2.114. 

- [5] M. Baum, V. Buchhold, J. Sauer, D. Wagner, dan T. Zündorf, “UnLimited TRAnsfers for Multi-Modal Route Planning: An Efficient Solution,” dalam _27th Annual European Symposium on Algorithms (ESA 2019)_ , Leibniz International Proceedings in Informatics (LIPIcs), Feb 2023, hlm. 1–42. doi: 10.4230/LIPIcs.ESA.2019.14. 

- [6] A. Idri, M. Oukarfi, A. Boulmakoul, K. Zeitouni, dan A. Masri, “A new time-dependent shortest path algorithm for multimodal transportation network,” _Procedia Comput. Sci._ , vol. 109, hlm. 692–697, 2017, doi: 10.1016/j.procs.2017.05.379. 

- [7] J.-P. Rodrigue, _The Geography of Transport Systems_ . Fifth edition. | Abingdon, Oxon ; New York, NY : Routledge, 2020.: Routledge, 2020. doi: 10.4324/9780429346323. 

- [8] K. Deb, A. Pratap, S. Agarwal, dan T. Meyarivan, “A fast and elitist multiobjective genetic algorithm: NSGA-II,” _IEEE Transactions on Evolutionary Computation_ , vol. 6, no. 2, hlm. 182–197, Apr 2002, doi: 10.1109/4235.996017. 

- [9] S. Sutradhar, S. Sharmin, dan S. Islam, “A Review On IDA* - Iterative deepening algorithm Heuristics Search,” dalam _2022 6th International Conference on Trends in Electronics and Informatics (ICOEI)_ , IEEE, Apr 2022, hlm. 286–288. doi: 10.1109/ICOEI53556.2022.9776667. 

- [10] S. Farahmand-Tabar dan P. Afrasyabi, “Multi-modal Routing in Urban Transportation Network Using Multiobjective Quantum Particle Swarm Optimization,” dalam _Applied Multi-objective Optimization_ , N. Dey: Ed. 

12 

Springer, 2024, hlm. 133–154. doi: 10.1007/978-981-97-0353-1_7. 

- [11] B. G. Patrick, M. Almulla, dan M. M. Newborn, “An upper bound on the time complexity of iterative-deepeningA*,” _Ann. Math. Artif. Intell._ , vol. 5, no. 2–4, hlm. 265–277, Jun 1992, doi: 10.1007/BF01543478. 

- [12] K. Y. Chen, “An Improved A* Search Algorithm for Road Networks Using New Heuristic Estimation,” Jul 2022. doi: http://arxiv.org/abs/2208.00312. 

- [13] H. Faroqi dan M. saadi Mesgari, “Performance Comparison between the Multi-Colony and Multi-Pheromone ACO Algorithms for Solving the Multi-objective Routing Problem in a Public Transportation Network,” _Journal of Navigation_ , vol. 69, no. 1, hlm. 197–210, Jan 2016, doi: 10.1017/S0373463315000594. 

- [14] A. El-Geneidy, M. Grimsrud, R. Wasfi, P. Tétreault, dan J. Surprenant-Legault, “New evidence on walking distances to transit stops: identifying redundancies and gaps using variable service areas,” _Transportation (Amst)._ , vol. 41, no. 1, hlm. 193–210, Jan 2014, doi: 10.1007/s11116-013-9508-z. 

- [15] P. Georgakis, A. Almohammad, E. Bothos, B. Magoutas, K. Arnaoutaki, dan G. Mentzas, “Heuristic-Based Journey Planner for Mobility as a Service (MaaS),” _Sustainability_ , vol. 12, no. 23, hlm. 10140, Des 2020, doi: 10.3390/su122310140. 

- [16] K. Wei, V. Vaze, dan A. Jacquillat, “Transit Planning Optimization Under Ride-Hailing Competition and Traffic Congestion,” _Transportation Science_ , vol. 56, no. 3, hlm. 725–749, Mei 2022, doi: 10.1287/trsc.2021.1068. 

- [17] F. Poletti, P. Bösch, F. Ciari, dan K. Axhausen, “Public Transit Route Mapping for Large-Scale Multimodal Networks,” _ISPRS Int. J. Geoinf._ , vol. 6, no. 9, hlm. 268, Agu 2017, doi: 10.3390/ijgi6090268. 

- [18] L. Gao dan M. Zhan, “Route Optimization of Multimodal Transport Considering Regional Differences under Carbon Tax Policy,” _Sustainability_ , vol. 17, no. 13, hlm. 5743, Jun 2025, doi: 10.3390/su17135743. 

- [19] Y. Yue, W. Wang, J. Chen, dan Z. Du, “Evaluating the Capacity Coordination in the Urban Multimodal Transport Network,” _Applied Sciences_ , vol. 11, no. 17, hlm. 8109, Agu 2021, doi: 10.3390/app11178109. 

- [20] M. B. H. Taş, K. Özkan, İ. Sarıçiçek, dan A. Yazici, “Transportation Mode Selection Using Reinforcement Learning in Simulation of Urban Mobility,” _Applied Sciences_ , vol. 15, no. 2, hlm. 806, Jan 2025, doi: 10.3390/app15020806. 

- [21] D. Delling, T. Pajor, dan R. F. Werneck, “Round-Based Public Transit Routing,” _Transportation Science_ , vol. 49, no. 3, hlm. 591–604, Agu 2015, doi: 10.1287/trsc.2014.0534. 

- [22] J. Dibbelt, T. Pajor, B. Strasser, dan D. Wagner, “Connection Scan Algorithm,” _ACM Journal of Experimental Algorithmics_ , vol. 23, no. 1, Art. 1.7, hlm. 1–56, Okt 2018, doi: 10.1145/3274661. 

- [23] M. Chairi, Yossyafra, dan E. E. Putri, “Perencanaan Integrasi Layanan Operasional Antar Moda Railbus dan Angkutan Umum di Kota Padang Berdasarkan Waktu Tempuh Perjalanan,” _Jurnal Rekayasa Sipil (JRS-Unand)_ , vol. 13, no. 1, hlm. 1–12, 2017, doi: 10.25077/jrs.13.1.1-12.2017. 

- [24] A. R. Rahmatullah, D. I. K. Dewi, dan C. D. T. Nurmasari, “Integrasi Antar Transportasi Umum di Kota Semarang,” _Jurnal Pengembangan Kota_ , vol. 10, no. 1, hlm. 36–46, 2022, doi: 10.14710/jpk.10.1.36-46. 

13 

