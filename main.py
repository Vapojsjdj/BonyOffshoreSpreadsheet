from flask import Flask, request, jsonify
import re
import requests
import json
import os

app = Flask(__name__)

YOUTUBE_API_KEY = "AIzaSyBrGoN99TWZEpZJcCMTnY6P2VJw9C13n08"

def extract_video_id(url):
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/watch\?v=([^&]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtu\.be\/([^?]+)',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def get_video_markers(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    response = requests.get(url)
    html_content = response.text

    json_match = re.search(r"var ytInitialData = ({.*?});", html_content)
    
    if not json_match:
        return None

    json_str = json_match.group(1)
    data = json.loads(json_str)

    try:
        framework_updates = data.get('frameworkUpdates', {})
        entity_batch_update = framework_updates.get('entityBatchUpdate', {})
        mutations = entity_batch_update.get('mutations', [])

        for mutation in mutations:
            if mutation.get('entityKey', '').startswith('Egp'):
                payload = mutation.get('payload', {})
                macro_markers_list_entity = payload.get('macroMarkersListEntity', {})
                
                if macro_markers_list_entity:
                    return {
                        'externalVideoId': macro_markers_list_entity.get('externalVideoId'),
                        'markersList': macro_markers_list_entity.get('markersList', {})
                    }

        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def get_peak_rewatched_timestamps(data):
    markers = data['markersList'].get('markers', [])
    sorted_markers = sorted(markers, key=lambda x: float(x.get('intensityScoreNormalized', 0)), reverse=True)    
    top_markers = sorted_markers[:5]
    top_timestamps_seconds = []
    for marker in top_markers:
        start_millis = marker.get('startMillis', '0')
        if start_millis.isdigit():
            top_timestamps_seconds.append(int(start_millis) / 1000)
    return top_timestamps_seconds

def seconds_to_time_format(seconds):
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

@app.route('/analyze', methods=['POST'])
def analyze_video():
    video_url = request.json['url']
    video_id = extract_video_id(video_url)

    if not video_id:
        return jsonify({"error": "لم يتم العثور على معرف فيديو صالح في الرابط المدخل."})

    markers_data = get_video_markers(video_id)

    if not markers_data:
        return jsonify({"error": "لم يتم العثور على بيانات العلامات لهذا الفيديو."})

    top_timestamps = get_peak_rewatched_timestamps(markers_data)
    formatted_timestamps = [seconds_to_time_format(ts) for ts in top_timestamps]

    return jsonify({
        "video_id": video_id,
        "top_timestamps": formatted_timestamps
    })

@app.route('/search', methods=['GET'])
def search_videos():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "يرجى تقديم استعلام بحث."})

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={query}&type=video&key={YOUTUBE_API_KEY}&maxResults=50"
    response = requests.get(url)
    data = response.json()

    videos = []
    for item in data.get('items', []):
        video = {
            'id': item['id']['videoId'],
            'title': item['snippet']['title'],
            'thumbnail': item['snippet']['thumbnails']['medium']['url']
        }
        videos.append(video)

    return jsonify(videos)

@app.route('/')
def index():
    return """
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>تحليل YouTube</title>
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css" rel="stylesheet">
    <style>
        :root {
            --primary-color: #FF0000;
            --secondary-color: #282828;
            --background-color: #F9F9F9;
            --text-color: #333;
            --card-background: #FFFFFF;
        }
        body {
            font-family: 'Cairo', sans-serif;
            margin: 0;
            padding: 20px;
            background-color: var(--background-color);
            color: var(--text-color);
            transition: background-color 0.3s, color 0.3s;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: var(--card-background);
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: var(--primary-color);
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 20px;
        }
        h1 i {
            margin-left: 10px;
            font-size: 0.8em;
        }
        .search-container {
            display: flex;
            margin-bottom: 20px;
        }
        #searchQuery {
            flex-grow: 1;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 4px 0 0 4px;
            font-size: 16px;
        }
        #searchButton {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 0 4px 4px 0;
            cursor: pointer;
            font-size: 16px;
        }
        .card {
            background-color: var(--card-background);
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 20px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: var(--primary-color);
            margin-top: 0;
            display: flex;
            align-items: center;
        }
        .card h2 i {
            margin-left: 10px;
        }
        #videoPlayer {
            width: 100%;
            aspect-ratio: 16 / 9;
            margin-bottom: 20px;
            border-radius: 8px;
            overflow: hidden;
        }
        .video-item {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
            cursor: pointer;
            padding: 10px;
            border-radius: 4px;
            transition: background-color 0.2s;
        }
        .video-item:hover {
            background-color: #f0f0f0;
        }
        .video-item img {
            width: 120px;
            margin-left: 10px;
            border-radius: 4px;
        }
        .timestamp {
            cursor: pointer;
            color: var(--primary-color);
            text-decoration: underline;
        }
        #darkModeToggle {
            position: fixed;
            top: 20px;
            left: 20px;
            background-color: var(--secondary-color);
            color: white;
            border: none;
            padding: 10px;
            border-radius: 50%;
            cursor: pointer;
            font-size: 16px;
        }
        .dark-mode {
            --background-color: #121212;
            --text-color: #FFFFFF;
            --card-background: #1E1E1E;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1><i class="fab fa-youtube"></i> تحليل YouTube</h1>
        <div class="search-container">
            <input type="text" id="searchQuery" placeholder="ابحث عن فيديوهات">
            <button id="searchButton" onclick="searchVideos()"><i class="fas fa-search"></i></button>
        </div>
        <div id="videoPlayer"></div>
        <div id="result" class="card">
            <h2><i class="fas fa-chart-line"></i> اللقطات الخمس الأكثر مشاهدة</h2>
            <div id="timestamps"></div>
        </div>
        <div id="searchResults" class="card">
            <h2><i class="fas fa-list"></i> نتائج البحث</h2>
            <div id="videoList"></div>
        </div>
    </div>
    <button id="darkModeToggle" onclick="toggleDarkMode()"><i class="fas fa-moon"></i></button>

    <script src="https://www.youtube.com/iframe_api"></script>
    <script>
        let player;
        let isDarkMode = false;

        function onYouTubeIframeAPIReady() {
            console.log('YouTube API Ready');
        }

        async function searchVideos() {
            const query = document.getElementById('searchQuery').value;
            const searchResultsDiv = document.getElementById('videoList');
            searchResultsDiv.innerHTML = '<p>جارٍ البحث...</p>';

            try {
                const response = await fetch(`/search?query=${encodeURIComponent(query)}`);
                const videos = await response.json();

                if (videos.error) {
                    searchResultsDiv.textContent = videos.error;
                } else {
                    let resultsHtml = '';
                    videos.forEach(video => {
                        resultsHtml += `
                            <div class="video-item" onclick="loadVideo('${video.id}')">
                                <img src="${video.thumbnail}" alt="${video.title}">
                                <span>${video.title}</span>
                            </div>
                        `;
                    });
                    searchResultsDiv.innerHTML = resultsHtml;
                }
            } catch (error) {
                searchResultsDiv.textContent = 'حدث خطأ أثناء البحث: ' + error.message;
            }
        }

        async function loadVideo(videoId) {
            const videoPlayerDiv = document.getElementById('videoPlayer');
            const timestampsDiv = document.getElementById('timestamps');
            videoPlayerDiv.innerHTML = `<div id="player"></div>`;
            timestampsDiv.textContent = 'جارٍ تحليل الفيديو...';

            player = new YT.Player('player', {
                height: '360',
                width: '640',
                videoId: videoId,
                events: {
                    'onReady': onPlayerReady
                }
            });

            try {
                const response = await fetch('/analyze', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ url: `https://www.youtube.com/watch?v=${videoId}` }),
                });
                const data = await response.json();

                if (data.error) {
                    timestampsDiv.textContent = data.error;
                } else {
                    let result = "";
                    data.top_timestamps.forEach((timestamp, index) => {
                        result += `<p>${index + 1}. <span class="timestamp" onclick="seekTo('${timestamp}')">${timestamp}</span></p>`;
                    });
                    timestampsDiv.innerHTML = result;
                }
            } catch (error) {
                timestampsDiv.textContent = 'حدث خطأ أثناء تحليل الفيديو: ' + error.message;
            }
        }

        function onPlayerReady(event) {
            console.log('Player Ready');
        }

        function seekTo(timestamp) {
            if (player && player.seekTo) {
                const [hours, minutes, seconds] = timestamp.split(':').map(Number);
                const totalSeconds = hours * 3600 + minutes * 60 + seconds;
                player.seekTo(totalSeconds);
            }
        }

        function toggleDarkMode() {
            document.body.classList.toggle('dark-mode');
            isDarkMode = !isDarkMode;
            const icon = document.querySelector('#darkModeToggle i');
            icon.className = isDarkMode ? 'fas fa-sun' : 'fas fa-moon';
        }
    </script>
</body>
</html>
    """

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)