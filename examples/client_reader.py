import cv2
import sys

# Ganti dengan IP PC Server tempat Docker berjalan
STREAM_URL = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.1.100:8000/video_feed"


def main():
    cap = cv2.VideoCapture(STREAM_URL)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"[ERROR] Gagal membuka stream dari {STREAM_URL}")
        sys.exit(1)

    print(f"[INFO] Terhubung ke {STREAM_URL}. Tekan 'q' untuk keluar.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARN] Frame gagal dibaca, menghentikan stream...")
            break

        cv2.imshow("CamStream Client", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
