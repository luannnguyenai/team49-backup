import { AlertTriangle, X } from "lucide-react";

interface ErrorModalProps {
  message: string;
  onDismiss: () => void;
}

export default function ErrorModal({ message, onDismiss }: ErrorModalProps) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onDismiss}
    >
      <div
        className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-4 flex items-start gap-3">
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-red-100">
            <AlertTriangle className="h-5 w-5 text-red-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-900">
              Error Occurred
            </h3>
            <p className="mt-1 text-sm text-red-700">
              {message}
            </p>
          </div>
          <button
            type="button"
            onClick={onDismiss}
            className="text-red-400 hover:text-red-600"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="flex justify-end">
          <button
            type="button"
            onClick={onDismiss}
            className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
