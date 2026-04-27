"use client";

import { AlertTriangle } from "lucide-react";
import type { LearningProfile } from "../profile";
import { describeProfileChange, isProfilePathStale } from "../profile";

interface ProfileChangeBannerProps {
  previousProfile: LearningProfile | null;
  currentProfile: LearningProfile;
  generatedTopologyHash: string | null;
}

export default function ProfileChangeBanner({
  previousProfile,
  currentProfile,
  generatedTopologyHash,
}: ProfileChangeBannerProps) {
  if (!isProfilePathStale(generatedTopologyHash, currentProfile)) return null;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-950 md:flex-row md:items-center md:justify-between">
      <div className="flex gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="text-sm font-semibold">Profile path đã thay đổi</p>
          <p className="mt-1 text-sm">
            {previousProfile
              ? describeProfileChange(previousProfile, currentProfile)
              : "Path hiện tại khác path đã dùng để sinh lộ trình này."}
          </p>
          <p className="mt-1 text-xs text-amber-800">
            V1 chưa gọi replan backend. Planner sẽ giữ path đang có cho đến khi replan endpoint sẵn sàng.
          </p>
        </div>
      </div>
      <button
        type="button"
        disabled
        className="rounded-xl bg-amber-200 px-3 py-2 text-sm font-semibold text-amber-900 opacity-70"
      >
        Replan sắp có
      </button>
    </div>
  );
}
