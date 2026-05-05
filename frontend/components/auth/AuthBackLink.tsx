import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function AuthBackLink() {
  return (
    <div className="mt-6 flex justify-center">
      <Link
        href="/"
        className="inline-flex items-center gap-2 text-sm font-medium text-text-body transition-colors hover:text-primary-600"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        <span>Back to Landing Page</span>
      </Link>
    </div>
  );
}
