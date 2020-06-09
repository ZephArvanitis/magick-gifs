"""Retrieve Sentinel true color images and animate an island.
"""
import argparse
import calendar
import math
import os
import subprocess
from datetime import datetime


class MagickCommand:
    """The simplest possible wrapper for imagemagick, the command line utility.
    """
    def __init__(self, input_file, output_file):
        """Create basic command instance.
        """
        self.input_file = input_file
        self.output_file = output_file
        self._cmd = "convert {i}".format(i=input_file)

    @classmethod
    def animation_command(cls, input_files, output_file, pause_length=100):
        """Create an animation command.

        These are distinct from more "typical" commands, because you really
        do need arguments before the input file. In particular, -delay,
        -loop, and -dispose are used here.
        """
        if len(input_files) == 1 and "*" in input_files[0]:
            input_str = input_files[0]
        else:
            input_str = " ".join(input_files)

        cmd = MagickCommand("", output_file)
        cmd._cmd += " -delay {l} -loop 0 -dispose previous {i}".format(l=pause_length,
                                                                       i=input_str)
        return cmd

    def command(self):
        """Get final command.
        """
        if self._cmd.endswith(self.output_file):
            return self._cmd
        self._cmd += " {out}".format(out=self.output_file)
        return self._cmd

    def run(self, label, dryrun=True):
        """Either run the command (dryrun=False) or print the full command.
        """
        cmd = self.command()
        if not dryrun:
            retcode = subprocess.run([cmd], shell=True).returncode
            text = "success!" if retcode == 0 else "return code " + retcode
            print("{label}: {text}".format(label=label, text=text))
        else:
            print(label+":", cmd)

    # Add features to the command
    def add_crop(self, width, height, startx, starty):
        """Add a crop directive to the command.
        """
        crop_str = "{w}x{h}+{x}+{y}".format(w=width, h=height,
                                            x=startx, y=starty)
        self._cmd += " -crop {crop}".format(crop=crop_str)

    def add_circle(self, center, radius):
        """Add a circle drawing to the command.
        """
        offset_x = center[0] + radius
        offset_y = center[1]
        self._cmd += " -draw \"circle {centerx},{centery} {rx},{ry}\"".format(
            centerx=center[0], centery=center[1], rx=offset_x, ry=offset_y)

    def add_line(self, point1, point2):
        """Add a line drawing to the command.
        """
        self._cmd += " -draw \"line {x1},{y1} {x2},{y2}\"".format(
            x1=point1[0], x2=point2[0], y1=point1[1], y2=point2[1])

    def add_text(self, point, text):
        """Add text to the image being edited.
        """
        self._cmd += " -draw \"text {x},{y} '{text}'\"".format(x=point[0],
                                                               y=point[1],
                                                               text=text)

    # Drawing details: colors etc.
    def set_fill(self, newfill):
        """Set the fill color for imagemagick."""
        self._cmd += " -fill {f}".format(f=newfill)

    def set_stroke(self, newstroke):
        """Set the stroke color for imagemagick."""
        self._cmd += " -stroke {s}".format(s=newstroke)

    def set_strokewidth(self, width):
        """Set the stroke width (in pixels?) for imagemagick."""
        self._cmd += " -strokewidth {s}".format(s=width)

    def set_fontsize(self, size):
        """Set the font size (in pixels? points?) for imagemagick."""
        self._cmd += " -pointsize {s}".format(s=size)


TILES = {"Coronados": "RVP",
         "Danzante": "RVP",
         "Carmen": "RVP",
         "Monserrate": "RVP",
         "Catalana": "RWP"}


CROP_AREAS = {"Coronados": (800, 800, 6800, 700),
              "Danzante": (400, 800, 7275, 4350),
              "Carmen": (1900, 3200, 7600, 1500),
              "Monserrate": (800, 1200, 9300, 5200),
              "Catalana": (800, 1500, 1800, 5500)}


def crop_to_island_command(input_file, island, output_file):
    """Generate the command to crop to an island.
    """
    # Get island extent (obtained manually)
    (width, height, islandx, islandy) = CROP_AREAS[island]
    # Crop to given range of pixels.
    cmd = MagickCommand(input_file, output_file)
    cmd.add_crop(width, height, islandx, islandy)
    return cmd


def add_calendar(cmd, center, radius):
    """Add a calendar annotation to an existing command.

    This includes the calendar circle, month ticks, and month labels.
    """
    cmd.set_strokewidth(3)
    cmd.set_fill('none')
    cmd.set_stroke('white')
    cmd.add_circle(center, radius)

    (centerx, centery) = center
    outer_r = radius * 1.2
    for i in range(12):
        theta = -math.pi / 2 + 2 * math.pi / 12 * i
        point1 = (int(math.cos(theta) * radius + centerx),
                  int(math.sin(theta) * radius + centery))
        point2 = (int(math.cos(theta) * outer_r + centerx),
                  int(math.sin(theta) * outer_r + centery))
        cmd.add_line(point1, point2)

    # Month annotations
    cmd.set_fontsize(radius / 6)
    cmd.add_text((centerx - radius/8, centery - radius + radius/4.5), 'Jan')
    cmd.add_text((centerx - radius/8, centery + radius - radius/27), 'Jul')
    cmd.add_text((centerx + radius - radius/3.2, centery + radius/16), 'Apr')
    cmd.add_text((centerx - radius + radius/40, centery + radius/13), 'Oct')

    return cmd


def add_marker(cmd, center, radius, date):
    """Add info about the image date to an existing annotation command.

    This includes the red tick mark and the current year.
    """
    month_fraction = date.day / calendar.mdays[date.month]
    theta = 2 * math.pi / 12 * (date.month - 1 + month_fraction)
    theta -= math.pi / 2
    (centerx, centery) = center
    markerradius = radius + 5
    outer_r = radius * 1.2
    outer_r *= 1.11
    point1 = (int(math.cos(theta) * markerradius + centerx),
              int(math.sin(theta) * markerradius + centery))
    point2 = (int(math.cos(theta) * outer_r + centerx),
              int(math.sin(theta) * outer_r + centery))
    cmd.set_strokewidth(5)
    cmd.set_stroke('red')
    cmd.add_line(point1, point2)

    # Text annotations
    # Year in the center
    textx = centerx - radius/2
    texty = centery + radius/5.3
    cmd.set_fontsize(radius / 2)
    cmd.set_fill('white')
    cmd.set_stroke('none')
    cmd.add_text((textx, texty), date.year)
    return cmd


def annotate_date_command(input_file, island, date, output_file):
    """Generate the command to add a date annotation to an image.

    Basically this figures out where to put the annotation (usually bottom
    right, sometimes bottome left), then generates a command for the
    calendar and date mark.
    """
    cmd = MagickCommand(input_file, output_file)
    (width, height, _, _) = CROP_AREAS[island]
    radius = int(min(width, height) / 10)
    (centerx, centery) = (width - radius * 1.5, height - radius * 1.5)
    if island == "Catalana":
        centerx = radius * 1.5
    center = (centerx, centery)
    cmd = add_calendar(cmd, center, radius)
    cmd = add_marker(cmd, center, radius, date)
    return cmd


def create_animation(island, homedir, destination, dryrun=True):
    """Create an animation based on island crops from a passed directory.

    Parameters:
        - island (string): one of ["Coronados", "Danzante", "Carmen",
            "Monserrate", "Catalana"]
        - homedir (string): path to sentinel TCIs
        - destination (string): filename to save the animation to
    """
    all_files = [x for x in os.listdir(homedir)
                 if x.startswith('T12{tile}'.format(tile=TILES[island]))
                 and x.endswith('TCI.jpg')]
    all_files.sort()
    print("Going to process:")
    print("  " + "\n  ".join(all_files))

    intermediate_files = []
    gif_files = []

    for filename in all_files:
        date_str = filename[7:15]
        file_date = datetime.strptime(date_str, '%Y%m%d')
        print("processing", file_date.date(), "("+filename+")")
        # Crop
        input_file = "{path}/{file}".format(path=homedir, file=filename)
        output_file = "rvp_{datestr}.jpg".format(datestr=date_str)
        cmd = crop_to_island_command(input_file, island, output_file)
        cmd.run(label="    crop", dryrun=dryrun)
        if not dryrun:
            intermediate_files.append(output_file)
        input_file = output_file
        output_file = "rvp_{date}_annotated.jpg".format(date=date_str)
        cmd = annotate_date_command(input_file, island, file_date, output_file)
        cmd.run(label="    annotate", dryrun=dryrun)
        # output_file = crop_and_annotate_file(island, homedir, filename,
        #                                      dryrun=dryrun)
        gif_files.append(output_file)
        if not dryrun:
            intermediate_files.append(output_file)

    # Animate
    if destination is None:
        destination = "{i}-animated.gif".format(i=island.lower())
    cmd = MagickCommand.animation_command(gif_files, destination)
    cmd.run(label="animate", dryrun=dryrun)

    # Clean up files we created
    for filename in intermediate_files:
        os.remove(filename)

def get_args():
    """Create parser and parse arguments from command line.
    """
    parser = argparse.ArgumentParser(description="Animate sentinel images")
    parser.add_argument("input_directory", help="directory location of TCI files")
    parser.add_argument('island', choices=['danzante', 'coronados',
                                           'carmen', 'monserrate',
                                           'catalana'],
                        help="island to animate")
    parser.add_argument("-d", "--destination", type=str,
                        help="destination gif file", required=False)
    parser.add_argument("--run", action='store_true',
                        help="Actually run the imagemagick commands")
    return parser.parse_args()

if __name__ == "__main__":
    ARGS = get_args()
    print(ARGS)
    create_animation(ARGS.island.title(), ARGS.input_directory,
                     ARGS.destination, dryrun=not ARGS.run)
