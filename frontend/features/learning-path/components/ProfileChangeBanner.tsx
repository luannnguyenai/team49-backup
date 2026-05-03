"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";
import type { LearningProfile } from "../profile";
import { describeProfileChange, isProfilePathStale } from "../profile";

interface ProfileChangeBannerProps {
  previousProfile: LearningProfile | null;
  currentProfile: LearningProfile;
  generatedTopologyHash: string | null;
  onRefreshPath?: () => void;
  refreshing?: boolean;
}

export default function ProfileChangeBanner({
  previousProfile,
  currentProfile,
  generatedTopologyHash,
  onRefreshPath,
  refreshing = false,
}: ProfileChangeBannerProps) {
  if (!isProfilePathStale(generatedTopologyHash, currentProfile)) return null;

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-950 md:flex-row md:items-center md:justify-between">
      <div className="flex gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
        <div>
          <p className="text-sm font-semibold">Your profile path changed</p>
          <p className="mt-1 text-sm">
            {previousProfile
              ? describeProfileChange(previousProfile, currentProfile)
              : "The current path differs from the one used to generate this learning path."}
          </p>
          <p className="mt-1 text-xs text-amber-800">
            The planner will rebuild the path from your new profile while keeping existing progress history.
          </p>
        </div>
      </div>
      <button
        type="button"
        onClick={onRefreshPath}
        disabled={refreshing || !onRefreshPath}
        className="inline-flex items-center justify-center gap-2 rounded-xl bg-amber-200 px-3 py-2 text-sm font-semibold text-amber-950 transition hover:bg-amber-300 disabled:cursor-not-allowed disabled:opacity-70"
      >
        <RefreshCw className={refreshing ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
        {refreshing ? "Rebuilding..." : "Rebuild learning path"}
      </button>
    </div>
  );
}
