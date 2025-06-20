from flask import Flask, request, jsonify
from TikTokApi import TikTokApi

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ TikTokApi Flask API جاهز!"

@app.route('/api/download', methods=['POST'])
def download_video():
    video_url = request.form.get('url')
    if not video_url:
        return jsonify({'status': 'error', 'message': 'يرجى إدخال رابط الفيديو'}), 400

    try:
        with TikTokApi() as api:
            video = api.video(url=video_url)
            video_bytes = video.bytes()

            filename = 'downloaded_video.mp4'
            with open(filename, 'wb') as f:
                f.write(video_bytes)

        return jsonify({'status': 'success', 'message': f'تم حفظ الفيديو في {filename}'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
