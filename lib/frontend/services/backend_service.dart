// Backend service for online detection using Ultralytics server
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:flutter/foundation.dart' show kIsWeb;

class BackendDetectionService {
  final String serverUrl;

  // Render server URL - deployed on Render cloud platform
  // Service URL: https://yieldmate-api.onrender.com
  static String get defaultServerUrl {
    // Use Render URL for all platforms
    return 'https://yieldmate-api.onrender.com';
  }

  BackendDetectionService({String? serverUrl})
      : serverUrl = serverUrl ?? defaultServerUrl;

  /// Detect fruits using backend server
  Future<List<Map<String, dynamic>>> detectFruits(File imageFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$serverUrl/detect'),
      );

      // Add image file
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      // Send request with timeout
      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 30),
        onTimeout: () {
          throw Exception('Request timeout - server may be unreachable');
        },
      );

      var response = await http.Response.fromStream(streamedResponse);
      var responseData = jsonDecode(response.body);

      if (response.statusCode == 200 && responseData['success'] == true) {
        // Format detections for the app
        List<Map<String, dynamic>> detections = [];
        for (var det in responseData['detections']) {
          final bbox = det['bbox'] as List;
          detections.add({
            'detectedClass': det['class'] as String,
            'confidenceInClass': (det['confidence'] as num).toDouble(),
            'rect': Rect.fromLTRB(
              (bbox[0] as num).toDouble(), // x1
              (bbox[1] as num).toDouble(), // y1
              (bbox[2] as num).toDouble(), // x2
              (bbox[3] as num).toDouble(), // y2
            ),
          });
        }
        return detections;
      } else {
        throw Exception(responseData['error'] ?? 'Unknown error from server');
      }
    } catch (e) {
      print('❌ Backend detection error: $e');
      rethrow;
    }
  }

  /// Detect fruits with tracking for live detection
  Future<Map<String, dynamic>> detectFruitsLive(File imageFile) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$serverUrl/detect_live'),
      );

      // Add image file
      request.files.add(
        await http.MultipartFile.fromPath('image', imageFile.path),
      );

      // Send request with timeout
      var streamedResponse = await request.send().timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          throw Exception('Request timeout - server may be unreachable');
        },
      );

      var response = await http.Response.fromStream(streamedResponse);
      var responseData = jsonDecode(response.body);

      if (response.statusCode == 200 && responseData['success'] == true) {
        // Format tracked objects
        List<Map<String, dynamic>> trackedObjects = [];
        for (var obj in responseData['tracked_objects']) {
          final bbox = obj['bbox'] as List;
          trackedObjects.add({
            'id': obj['id'],
            'class': obj['class'],
            'bbox': bbox,
            'rect': Rect.fromLTRB(
              (bbox[0] as num).toDouble(), // x1
              (bbox[1] as num).toDouble(), // y1
              (bbox[2] as num).toDouble(), // x2
              (bbox[3] as num).toDouble(), // y2
            ),
            'confidence': (obj['confidence'] as num).toDouble(),
            'frames_seen': obj['frames_seen'],
          });
        }

        return {
          'tracked_objects': trackedObjects,
          'total_count': responseData['total_count'] ?? 0,
          'new_count_this_frame': responseData['new_count_this_frame'] ?? 0,
          'active_objects': responseData['active_objects'] ?? 0,
        };
      } else {
        throw Exception(responseData['error'] ?? 'Unknown error from server');
      }
    } catch (e) {
      print('❌ Live detection error: $e');
      rethrow;
    }
  }

  /// Reset tracker for new counting session
  Future<bool> resetTracker() async {
    try {
      var response = await http
          .post(Uri.parse('$serverUrl/reset_tracker'))
          .timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        var responseData = jsonDecode(response.body);
        return responseData['success'] == true;
      }
      return false;
    } catch (e) {
      print('❌ Reset tracker error: $e');
      return false;
    }
  }

  /// Check if server is reachable
  Future<bool> checkHealth() async {
    try {
      print('🔍 Checking server health at: $serverUrl/health');
      var response = await http.get(Uri.parse('$serverUrl/health')).timeout(
        const Duration(seconds: 10),
        onTimeout: () {
          print('⏱️ Health check timeout - server may be unreachable');
          throw Exception('Connection timeout');
        },
      );

      print('📊 Health check response: ${response.statusCode}');
      print('📄 Response body: ${response.body}');

      if (response.statusCode == 200) {
        print('✅ Server is healthy');
        return true;
      } else {
        print('❌ Server returned status: ${response.statusCode}');
        return false;
      }
    } on SocketException catch (e) {
      print('❌ Network error: ${e.message}');
      print('💡 Make sure:');
      print('   1. Backend server is running');
      print('   2. Server URL is correct: $serverUrl');
      print('   3. Device/emulator can reach the server');
      return false;
    } on HttpException catch (e) {
      print('❌ HTTP error: ${e.message}');
      return false;
    } catch (e) {
      print('❌ Server health check failed: $e');
      print('💡 Server URL: $serverUrl');
      print('💡 Make sure the backend server is running');
      return false;
    }
  }
}
