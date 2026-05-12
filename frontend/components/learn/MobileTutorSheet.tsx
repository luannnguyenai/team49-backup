"use client";

import BottomSheet from "@/components/ui/BottomSheet";

type MobileTutorSheetProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  children: React.ReactNode;
};

export default function MobileTutorSheet({
  open,
  onOpenChange,
  children,
}: MobileTutorSheetProps) {
  return (
    <BottomSheet
      open={open}
      onOpenChange={onOpenChange}
      title="AI Tutor"
      panelClassName="max-h-[85vh]"
    >
      <div className="-mx-4 -my-2 min-h-[26rem] overflow-hidden">
        {children}
      </div>
    </BottomSheet>
  );
}
