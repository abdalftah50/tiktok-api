import yt_dlp
import os

def get_download_url(video_url):
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'skip_download': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return {
                'status': 'success',
                'title': info.get('title'),
                'url': info.get('url'),
                'author': info.get('uploader')
            }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}