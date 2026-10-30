/// Utility for formatting duration and timestamps
abstract class TimeFormat {
  /// Formats seconds or Duration into mm:ss
  static String formatDuration(Duration duration) {
    final minutes = duration.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = duration.inSeconds.remainder(60).toString().padLeft(2, '0');
    return '$minutes:$seconds';
  }

  /// Formats milliseconds into mm:ss
  static String formatMs(int ms) {
    return formatDuration(Duration(milliseconds: ms));
  }

  /// Formats DateTime into a concise display string: e.g. "Today, 10:30 AM" or "Oct 30, 10:30 AM"
  static String formatRelativeDate(DateTime dateTime) {
    final now = DateTime.now();
    final isToday =
        now.year == dateTime.year &&
        now.month == dateTime.month &&
        now.day == dateTime.day;
    final hour = dateTime.hour > 12
        ? dateTime.hour - 12
        : (dateTime.hour == 0 ? 12 : dateTime.hour);
    final ampm = dateTime.hour >= 12 ? 'PM' : 'AM';
    final minute = dateTime.minute.toString().padLeft(2, '0');
    final timeStr = '$hour:$minute $ampm';

    if (isToday) {
      return 'Today, $timeStr';
    }

    final months = [
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    final monthStr = months[dateTime.month - 1];
    return '$monthStr ${dateTime.day}, $timeStr';
  }
}
