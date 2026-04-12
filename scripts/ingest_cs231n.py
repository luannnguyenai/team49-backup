import glob
import os

from src.services.ingestion import ingest_lecture


def find_file(directory, pattern):
    files = glob.glob(os.path.join(directory, pattern))
    return files[0] if files else None


def main():
    base_dir = "data/cs231n"
    toc_dir = os.path.join(base_dir, "ToC_Summary")
    transcript_dir = os.path.join(base_dir, "transcripts")
    video_dir = os.path.join(base_dir, "videos")

    # Loop through lecture numbers 1 to 18
    for n in range(1, 19):
        lecture_id = f"lecture-{n}"

        # 1. Find ToC
        toc_path = os.path.join(toc_dir, f"lecture-{n}.json")
        if not os.path.exists(toc_path):
            # Try alternate path
            toc_path = os.path.join(base_dir, "slides", "ToC_Summary", f"lecture-{n}.json")
            if not os.path.exists(toc_path):
                print(f"Skipping {lecture_id}: ToC not found")
                continue

        # 2. Find Transcript
        # Pattern: ...Lecture_{n}_transcript.txt or ...Lecture_{n}_...
        transcript_pattern = f"*Lecture_{n}_*.txt"
        transcript_path = find_file(transcript_dir, transcript_pattern)
        if not transcript_path:
            # Try without underscore
            transcript_pattern = f"*Lecture {n}*.txt"
            transcript_path = find_file(transcript_dir, transcript_pattern)

        if not transcript_path:
            print(f"Warning for {lecture_id}: Transcript not found")
            transcript_paths = []
        else:
            transcript_paths = [transcript_path]

        # 3. Find Video
        # Pattern: ...Lecture {n}：... or ...Lecture {n}...
        video_pattern = f"*Lecture {n}*.mp4"
        video_path = find_file(video_dir, video_pattern)

        if not video_path:
            # Try with colon (some have Lec X: ...)
            video_pattern = f"*Lecture {n}：*.mp4"
            video_path = find_file(video_dir, video_pattern)

        if not video_path:
            print(f"Warning for {lecture_id}: Video not found")
            video_rel_path = None
        else:
            # Convert to path relative to 'data' directory
            # e.g. data/cs231n/videos/X.mp4 -> cs231n/videos/X.mp4
            # Then UI uses /data/cs231n/videos/X.mp4
            video_rel_path = os.path.relpath(video_path, "data")
            # Ensure it starts with 'data/' prefix if that's what UI expects
            # Actually index.html does: video.src = `/${lec.video_url}`;
            # So if video_url is 'data/cs231n/videos/X.mp4', it becomes '/data/cs231n/videos/X.mp4'
            video_rel_path = os.path.join("data", video_rel_path)

        print(f"Ingesting {lecture_id}...")
        print(f"  ToC: {toc_path}")
        print(f"  Transcript: {transcript_path}")
        print(f"  Video: {video_path}")

        try:
            ingest_lecture(
                lecture_id=lecture_id,
                toc_path=toc_path,
                transcript_paths=transcript_paths,
                video_rel_path=video_rel_path,
            )
        except Exception as e:
            print(f"FAILED to ingest {lecture_id}: {e}")
            continue


if __name__ == "__main__":
    main()
