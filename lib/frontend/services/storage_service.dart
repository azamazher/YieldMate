// ============================================================================
// STORAGE SERVICE - DETECTION HISTORY
// ============================================================================
// Service to save and load detection history for calendar

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/detection_record.dart';

class StorageService {
  static const String _key = 'detection_history';

  // Save detection record
  static Future<void> saveDetection(DetectionRecord record) async {
    final prefs = await SharedPreferences.getInstance();
    final history = await getDetectionHistory();
    
    // Check if record for this date already exists
    final existingIndex = history.indexWhere((r) => r.date == record.date);
    
    if (existingIndex != -1) {
      // Update existing record (merge counts)
      final existing = history[existingIndex];
      final mergedCounts = Map<String, int>.from(existing.fruitCounts);
      
      // Add new counts to existing
      record.fruitCounts.forEach((fruit, count) {
        mergedCounts[fruit] = (mergedCounts[fruit] ?? 0) + count;
      });
      
      history[existingIndex] = DetectionRecord(
        date: record.date,
        fruitCounts: mergedCounts,
        imagePath: record.imagePath ?? existing.imagePath,
        timestamp: record.timestamp,
      );
    } else {
      // Add new record
      history.add(record);
    }
    
    // Sort by date (newest first)
    history.sort((a, b) => b.timestamp.compareTo(a.timestamp));
    
    // Save to storage
    final jsonList = history.map((r) => r.toJson()).toList();
    await prefs.setString(_key, jsonEncode(jsonList));
  }

  // Get all detection history
  static Future<List<DetectionRecord>> getDetectionHistory() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_key);
    
    if (jsonString == null) {
      return [];
    }
    
    try {
      final jsonList = jsonDecode(jsonString) as List;
      return jsonList
          .map((json) => DetectionRecord.fromJson(json as Map<String, dynamic>))
          .toList();
    } catch (e) {
      print('Error loading detection history: $e');
      return [];
    }
  }

  // Get detection for specific date
  static Future<DetectionRecord?> getDetectionForDate(String date) async {
    final history = await getDetectionHistory();
    try {
      return history.firstWhere((r) => r.date == date);
    } catch (e) {
      return null;
    }
  }

  // Clear all history
  static Future<void> clearHistory() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_key);
  }
}

