from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ TikTok Video Downloader API جاهز!"

@app.route('/api/download', methods=['POST'])
def download():
    video_url = request.form.get('url')
    if not video_url:
        return jsonify({'status': 'error', 'message': 'يرجى إدخال رابط الفيديو'}), 400

    ydl_opts = {
        'format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,  # لا تحمل الملف فقط استخرج روابط
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            # أفضل رابط فيديو mp4 بدقة عالية
            formats = info.get('formats', [])
            best_format = next((f for f in formats if f.get('ext') == 'mp4' and f.get('vcodec') != 'none'), None)

            if best_format:
                return jsonify({
                    'status': 'success',
                    'title': info.get('title'),
                    'author': info.get('uploader'),
                    'download_url': best_format.get('url')
                })
            else:
                return jsonify({'status': 'error', 'message': 'تعذر إيجاد رابط تحميل صالح'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
