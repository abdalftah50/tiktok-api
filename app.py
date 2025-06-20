from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route('/api/tiktok', methods=['POST'])
def download_tiktok():
    url = request.form.get('url')
    if not url:
        return jsonify({'status': 'error', 'message': 'الرجاء إدخال رابط TikTok'}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'forceurl': True
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            download_url = info.get('url')

        return jsonify({
            'status': 'success',
            'title': info.get('title'),
            'author': info.get('uploader'),
            'download_url': download_url
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)