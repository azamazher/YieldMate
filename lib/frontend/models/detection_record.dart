// ============================================================================
// DETECTION RECORD MODEL
// ============================================================================
// Model to store detection history for calendar

class DetectionRecord {
  final String date; // Format: YYYY-MM-DD
  final Map<String, int> fruitCounts; // e.g., {'apple': 5, 'orange': 3}
  final String? imagePath; // Optional: path to the detected image
  final DateTime timestamp;

  DetectionRecord({
    required this.date,
    required this.fruitCounts,
    this.imagePath,
    required this.timestamp,
  });

  // Convert to JSON for storage
  Map<String, dynamic> toJson() {
    return {
      'date': date,
      'fruitCounts': fruitCounts,
      'imagePath': imagePath,
      'timestamp': timestamp.toIso8601String(),
    };
  }

  // Create from JSON
  factory DetectionRecord.fromJson(Map<String, dynamic> json) {
    return DetectionRecord(
      date: json['date'] as String,
      fruitCounts: Map<String, int>.from(json['fruitCounts'] as Map),
      imagePath: json['imagePath'] as String?,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }

  // Get total fruit count
  int get totalCount {
    return fruitCounts.values.fold(0, (sum, count) => sum + count);
  }
}

