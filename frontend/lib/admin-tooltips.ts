import type { KpiTooltip } from "@/components/admin/KpiCard";

export const overviewTooltips = {
  totalUsers: {
    summary: "Tong so user da duoc tao trong he thong.",
    detail: "Dem tu bang users. Day la cumulative metric, khong phan anh muc do active hien tai.",
  },
  dau: {
    summary: "So user hoat dong trong 24 gio gan nhat.",
    detail: "Uoc tinh tu sessions theo user distinct trong 24h. Huu ich de theo doi usage ngan han.",
  },
  mau: {
    summary: "So user hoat dong trong 30 ngay gan nhat.",
    detail: "Uoc tinh tu sessions theo user distinct trong 30 ngay. Dung de nhin muc do giu chan tong quat.",
  },
  signups7d: {
    summary: "So user dang ky moi trong 7 ngay gan nhat.",
    detail: "Dem tu users.created_at. Dung de theo doi tang truong dau vao.",
  },
  activeNow: {
    summary: "So user duoc xem la dang hoat dong luc nay.",
    detail: "Uoc tinh tu session gan day hoac session chua dong trong khoang ngan. Day la near-real-time signal, khong phai so tuyet doi chinh xac.",
  },
  llmCalls24h: {
    summary: "Tong so luot goi LLM trong 24 gio gan nhat.",
    detail: "Dem tu du lieu lich su hoi dap. Dung de theo doi tai AI va muc su dung tutor.",
  },
  modelCurrent: {
    summary: "Model mac dinh backend dang cau hinh de phuc vu request.",
    detail: "Lay tu config runtime. Day la thong tin cau hinh, khong phai metric hieu nang.",
  },
  errorRate: {
    summary: "Ty le request backend bi loi phia server.",
    detail: "Tinh tu HTTP 5xx / tong request trong 5 phut gan nhat tu Prometheus. Neu tang lien tuc thi can kiem tra backend hoac upstream.",
  },
} satisfies Record<string, KpiTooltip>;

export const llmTooltips = {
  callsWindow: {
    summary: "Tong so luot goi LLM trong cua so thoi gian dang xem.",
    detail: "Hien dang tong hop theo 24h tu qa_history.jsonl. Dung de theo doi luu luong tutor AI.",
  },
  errorsWindow: {
    summary: "So luot goi LLM bi danh dau loi trong cua so thoi gian.",
    detail: "Doc tu log qa_history.jsonl. Neu tang, can doi chieu voi latency, provider status, va log chi tiet.",
  },
  firstStatusP95: {
    summary: "95% request nhan duoc tin hieu trang thai dau tien nhanh hon moc nay.",
    detail: "Tinh tu Prometheus theo bucket 1 gio. Day la tin hieu dau tien cua stream bat dau phan hoi.",
  },
  firstStatusP50: {
    summary: "Mot nua request nhan duoc tin hieu trang thai dau tien nhanh hon moc nay.",
    detail: "Giup nhin do tre dien hinh thay vi chi nhin tail latency.",
  },
  firstAnswerP95: {
    summary: "95% request nhan duoc phan noi dung tra loi dau tien nhanh hon moc nay.",
    detail: "Day gan voi TTFT trong streaming tutor. Neu tang cao, trai nghiem nguoi dung se thay cham ro ret.",
  },
  firstAnswerP50: {
    summary: "Mot nua request nhan duoc phan noi dung tra loi dau tien nhanh hon moc nay.",
    detail: "Phan anh toc do phan hoi dien hinh cua tutor trong dieu kien binh thuong.",
  },
  positiveRatings: {
    summary: "So luot phan hoi tich cuc tu nguoi dung.",
    detail: "Dem tu qa_history.rating = 1 trong 14 ngay gan nhat. Dung de theo doi chat luong cam nhan.",
  },
  negativeRatings: {
    summary: "So luot phan hoi tieu cuc tu nguoi dung.",
    detail: "Dem tu qa_history.rating = -1 trong 14 ngay gan nhat. Nen doc cung recent negative feedback de hieu nguyen nhan.",
  },
  positiveRatio: {
    summary: "Ty le phan hoi tich cuc tren tong phan hoi da duoc cham.",
    detail: "Tinh tu positive / total rated trong 14 ngay. Huu ich hon khi xem cung sample size.",
  },
  unrated24h: {
    summary: "So luot tra loi chua duoc nguoi dung danh gia trong 24 gio gan nhat.",
    detail: "Dung de biet bao nhieu interaction chua co feedback, khong dong nghia voi tot hay xau.",
  },
} satisfies Record<string, KpiTooltip>;

export const trafficTooltips = {
  rps1m: {
    summary: "So request backend trung binh moi giay trong 1 phut gan nhat.",
    detail: "Lay tu Prometheus rate. Dung de theo doi tai he thong theo thoi gian thuc.",
  },
  p50Latency: {
    summary: "Mot nua request hoan thanh nhanh hon moc nay.",
    detail: "Phan anh do tre dien hinh cua API tu Prometheus trong cua so 5 phut.",
  },
  p95Latency: {
    summary: "95% request hoan thanh nhanh hon moc nay.",
    detail: "Dung de theo doi tail latency. Neu tang, mot nhom nguoi dung se cam thay he thong cham ro ret.",
  },
  p99Latency: {
    summary: "99% request hoan thanh nhanh hon moc nay.",
    detail: "Nhay voi outlier va spike. Huu ich de phat hien su co ngat quang.",
  },
  rate4xx: {
    summary: "Ty le request bi tu choi hoac sai tu phia client.",
    detail: "Tinh tu HTTP 4xx / tong request trong 5 phut. Tang cao co the do auth, route sai, hoac misuse tu frontend.",
  },
  rate5xx: {
    summary: "Ty le request loi phia server.",
    detail: "Tinh tu HTTP 5xx / tong request trong 5 phut. Day la chi bao chinh cho backend instability.",
  },
} satisfies Record<string, KpiTooltip>;

export const systemTooltips = {
  cpuUsage: {
    summary: "Muc su dung CPU hien tai cua may hoac runtime backend.",
    detail: "Lay tu psutil. Dung de phat hien tai xu ly tang cao hoac saturation.",
  },
  ramUsage: {
    summary: "Ty le bo nho dang duoc su dung.",
    detail: "Lay tu psutil. Neu tang lien tuc co the la dau hieu memory pressure hoac leak.",
  },
  diskUsage: {
    summary: "Ty le dung luong dia dang dung.",
    detail: "Lay tu psutil. Quan trong voi moi truong local hoac container neu log hoac data tang nhanh.",
  },
  dbConnections: {
    summary: "So ket noi hien co toi PostgreSQL.",
    detail: "Doc tu pg_stat_activity. Neu tang bat thuong co the lien quan connection leak hoac tai cao.",
  },
  redisHitRate: {
    summary: "Ty le cache hit cua Redis tren tong hit va miss.",
    detail: "Lay tu Redis INFO stats. Cao hon thuong tot hon, nhung can doc cung loai workload.",
  },
  serviceUptime: {
    summary: "Thoi gian backend process hien tai da chay lien tuc.",
    detail: "Tinh tu luc app boot. Neu thuong xuyen reset ve thap, co the app dang restart.",
  },
} satisfies Record<string, KpiTooltip>;
