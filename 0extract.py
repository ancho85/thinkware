# encoding: utf-8
import os
import re
import subprocess
from pathlib import Path

# Please specify the path where you have the MP4 video files coming from the dashcam
# The extracted images will be placed in subdirectories: video_path/img/F and video_path/img/R
video_path = str(Path(__file__).resolve().parent)

def extract_img(mp4name):
    # Determine if Front or Rear camera is used
    match = re.match(r"^REC_.*(F|R)\.MP4", mp4name)
    FR = match.group(1) if match else None

    # Get the prefix of the file
    match = re.match(r"^REC_(.*)\.MP4", mp4name)
    prefix = match.group(1) if match else None

    # Remove and recreate temporary subtitle file containing GPS and g-sensor data
    tmp_srt = Path('tmp.srt')
    if tmp_srt.exists():
        tmp_srt.unlink()

    srtcmd = f"ffmpeg -nostats -loglevel 0 -i {mp4name} -an -vn tmp.srt"
    subprocess.run(srtcmd, shell=True)
    print(f"{srtcmd}\n")

    with tmp_srt.open('r') as fh:
        n = 0
        for row in fh.read().split("\n"):
            row = row.strip()

            # G-sensor frames each 100ms and GPS frames every second
            # Check from NMEA RMC sentence to detect GPS frame
            # match = re.match(r"^[A-Z](.*RMC.*)\*", row)
            match = re.match(r"(.*RMC.*)\*", row)
            if match:
                n += 1
                if n == 60:
                    continue  # no more frames in the mp4 file!
                tocsum = match.group(1)

                a, b, c, d, e, sentence, time, status, lat, latNS, lon, lonWE, speedKN, orientation, date, magnet, mag2, csum = row.split(',')

                lat = re.sub(r'^([0-9][0-9])(.*)', r'\1 \2', lat)
                lon = re.sub(r'^([0-9][0-9][0-9])(.*)', r'\1 \2', lon)
                time = re.sub(r'^([0-9]{2})([0-9]{2})([0-9]{2})', r'\1:\2:\3', time)
                date = re.sub(r'^([0-9]{2})([0-9]{2})([0-9]{2})$', r'20\3:\2:\1', date)

                # For rear view, we add 180° to the orientation
                if FR == 'R':
                    orientation_match = re.match(r'^([0-9]+)\.([0-9]+)', orientation)
                    if orientation_match:
                        orientation = f"{(int(orientation_match.group(1)) + 180) % 360:03}.{orientation_match.group(2)}"

                # Calculate NMEA checksum
                # csum = re.sub(r'.*\*([0-9A-F][0-9A-F]).*\r\n+', r'\1', csum)
                # csum2 = csum.replace('\R', '')
                # uff = 0
                # for char in tocsum:
                #     uff ^= ord(char)
                # calccsum = f"{uff:X}"

                if True:  # csum == calccsum or csum2 == calccsum:
                    fn = f"{FR}/{prefix}_{n:02}.jpg"
                    print(fn)

                    # Extract 1 frame as jpg each second
                    #extractcmd = f"avconv -nostats -loglevel 0 -ss {n} -i {mp4name} -frames:v 1 -vf 'crop=1920:1000:0:0,scale=1920:1080' -qscale 1 -f image2 'img/{fn}'"
                    extractcmd =  f"ffmpeg -nostats -loglevel 0 -ss {n} -skip_frame nokey -i {mp4name} -frames:v 1 -qscale 1 -f image2 -vsync vfr img/{fn}"
                    subprocess.run(extractcmd, shell=True)

                    # Tag the jpg file with EXIF GPS data
                    exifcmd =  f"exiftool -q -overwrite_original -exif:datetimeoriginal=\"{date} {time}\" "
                    exifcmd += f"-exif:gpslatitude=\"{lat}\" -exif:gpslatituderef={latNS} -exif:gpslongitude=\"{lon}\" "
                    exifcmd += f"-exif:gpslongituderef={lonWE} -exif:gpsimgdirection={orientation} -exif:gpsstatus#={status} "
                    exifcmd += f"-exif:gpstimestamp=\"{time}\" -exif:gpsdatestamp=\"{date}\" img/{fn}"
                    subprocess.run(exifcmd, shell=True)
                # else:
                #     print(f"Invalid GPS checksum {csum} VS {calccsum}")

if __name__ == "__main__":
    os.chdir(video_path)

    # Check for subdirs
    if not (Path(video_path) / "img/F").is_dir() or not (Path(video_path) / "img/R").is_dir():
        raise FileNotFoundError(f"Missing {video_path}/img/F or {video_path}/img/R subdirectories")

    data_dir = Path('.')
    files = sorted(data_dir.iterdir())

    for file in files:
        name = file.name
        if re.match(r"^REC_.*(F|R).MP4", name):
            print(f"{name} : {re.match(r'.*(F|R)', name).group(1)}")
            extract_img(name)

    # print("Images have been extracted. Now you can use mapillary_tools (do not forget to export global MAPILLARY_ variable):")
    # print(f"remove_duplicates.py {video_path}/img/F/ {video_path}/dup/")
    # print(f"sequence_split.py {video_path}/img/F/")
    # print(f"upload_with_authentication.py {video_path}/img/F/")
    print("Do not forget to do the same with rear views")
