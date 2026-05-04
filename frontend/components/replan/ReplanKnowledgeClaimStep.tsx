"use client";

interface Props {
  claim: string;
  message: string | null;
  onClaimChange: (claim: string) => void;
  onContinue: () => void;
}

export default function ReplanKnowledgeClaimStep({
  claim,
  message,
  onClaimChange,
  onContinue,
}: Props) {
  return (
    <>
      <div>
        <p className="text-sm font-medium" style={{ color: "var(--text-primary)" }}>
          Bạn đã biết phần nào rồi?
        </p>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Mô tả cụ thể những phần bạn đã nắm để hệ thống tạo bài kiểm tra xác nhận. Mô tả này không tự động bỏ qua bài học. Kết quả assessment mới được dùng để cập nhật lộ trình.
        </p>
      </div>

      {message && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-900/40 dark:bg-amber-900/20 dark:text-amber-200">
          {message}
        </div>
      )}

      <div className="rounded-xl border p-4" style={{ borderColor: "var(--border)" }}>
        <label
          htmlFor="replan-knowledge-claim"
          className="text-sm font-semibold"
          style={{ color: "var(--text-primary)" }}
        >
          Bạn đã biết phần nào rồi?
        </label>
        <textarea
          id="replan-knowledge-claim"
          aria-label="Bạn đã biết phần nào rồi?"
          value={claim}
          onChange={(event) => onClaimChange(event.target.value)}
          className="mt-3 min-h-28 w-full rounded-lg border px-3 py-2 text-sm outline-none focus:border-primary-500"
          style={{
            borderColor: "var(--border)",
            backgroundColor: "var(--bg-card)",
            color: "var(--text-primary)",
          }}
          placeholder={"Ví dụ:\n- Tôi đã nắm CNN, convolution, pooling.\n- Tôi biết Faster R-CNN nhưng chưa chắc YOLO.\n- Tôi hiểu object detection cơ bản, muốn kiểm tra để bỏ bớt phần nền tảng."}
        />
      </div>

      <div className="flex items-center justify-end pt-2">
        <button
          type="button"
          onClick={onContinue}
          className="rounded-xl bg-primary-600 px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-700 active:scale-[0.99]"
        >
          Continue
        </button>
      </div>
    </>
  );
}
