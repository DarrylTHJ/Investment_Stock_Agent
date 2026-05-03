fetch_data.py
- import os what is the purpose? OS-level file management is? when to use and when not
ANS : anythng to do with creating folders, checking file names extracted

- we use yt_dlp which is meant for downloading entire yt videos, but just using it to download the metadata (video id/titles) to be passed to another api (youtube_transcript_api). Is youtube_transcript_api incapable of extracted video ids as well? or isn't there a simpler way? sounds a little like we are doing unnecessary steps.
ANS : youtube_transcript_api cannot extract video id and title. It requires 

- give brief examples of how time and random works
ANS : time.sleep("seconds") and random.uniform("a","b")

    random_time = random.uniform(10,20)
    time.sleep(random_time)
    # letting the pc sleep at random time between 10 to 20 secs

- difference between the YoutubeTranscriptAPi and TextFormmatter that were imported? also what do you call these things that are imported? Functions? Methods?
ANS : YoutubeTranscriptAPi and TextFormmatter are CLASSES. The actions these classes can do are METHODS. Functions are just standalone code blocks

    CLASS = eg: TextFormmatter
    METHOD = eg: .format_transcript()
    FUNCTION = eg: sanitize_filename()

- speaking of functions and methods, what is the difference?
- what is the purpose of the textformatter here?
- about quiet = true, is it to remove any redundant logs from yt_dlp? where do these logs normally turn out? and what do we reduce it to?
- 