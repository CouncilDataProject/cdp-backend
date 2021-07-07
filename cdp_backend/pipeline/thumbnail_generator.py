import math

import imageio


def get_static_thumbnail(video_url: str, seconds: int = 30) -> str:
    """
    A function that produces a png thumbnail image from an mp4 video file

    Parameters
    ----------
    video_url: str, required
        The URL of the video from which the thumbnail will be produced
    seconds: int, optional
        Determines after how many seconds a frame will be selected to produce the
        thumbnail. The default is 30 seconds


    Returns
    -------
    str: cover_name
        The name of the thumbnail file: Always the same as the name of the video file,
        only a 'png' replaces the 'mp4'
    """

    if video_url[len(video_url) - 4 :] != ".mp4":
        raise ValueError(video_url + " is not an mp4 file")

    cover_name = video_url[0 : len(video_url) - 4] + ".png"

    reader = imageio.get_reader(video_url)

    frame_to_take = math.floor(reader.get_meta_data()["fps"] * seconds)

    # If the video is shorter than anticipated, produce a thumbnail from a frame near
    # the end of the video
    intermediate_image = 0

    for i, image in enumerate(reader):
        if i % 100 == 0:
            intermediate_image = image

        if i == frame_to_take:
            imageio.imwrite(cover_name, image)
            return cover_name

    imageio.imwrite(cover_name, intermediate_image)
    return cover_name


def get_hover_thumbnail(video_url: str, num_frames: int = 10) -> str:
    """
    A function that produces a gif hover thumbnail from an mp4 video file

    Parameters
    ----------
    video_url: str, required
        The URL of the video from which the thumbnail will be produced
    num_frames: int, optional
        Determines the number of frames in the thumbnail


    Returns
    -------
    str: cover_name
        The name of the thumbnail file: Always the same as the name of the video file,
        only a 'gif' replaces the 'mp4'
    """
    if video_url[len(video_url) - 4 :] != ".mp4":
        raise ValueError(video_url + " is not an mp4 file")

    count = 0
    reader = imageio.get_reader(video_url)

    for i, image in enumerate(reader):
        count += 1

    count = math.floor(count / num_frames)

    gif_path = video_url[0 : len(video_url) - 4] + ".gif"

    with imageio.get_writer(gif_path, mode="I") as writer:
        for i, image in enumerate(reader):
            if i != 0 and i % count == 0:
                writer.append_data(image)

    return gif_path
