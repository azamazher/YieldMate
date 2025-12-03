// Backend service for online detection using Ultralytics server
import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class BackendDetectionService {
  final String serverUrl;

  // Local development server URL
  // Update this IP to match your laptop's IP when testing on mobile device
  // Find your IP: macOS: ipconfig getifaddr en0 | Linux: hostname -I | Windows: ipconfig
  static String get defaultServerUrl {
    // For local development - update IP to your laptop's IP address
    // For Android Emulator: Use http://10.0.2.2:5000
    // For iOS Simulator: Use http://localhost:5000
    // For Physical Device: Use your laptop IP (e.g., http://172.20.10.3:5000)
    return 'http://172.20.10.3:5000'; // Update this to your laptop IP
  }

  BackendDetectionService({String? serverUrl})
      : serverUrl = serverUrl ?? defaultServerUrl;

  /// Detect fruits using backend server
  Future<List<Map<String, dynamic>>> detectFruits(File imageFile) async {
    int retryCount = 0;
    const maxRetries = 2; // Try up to 2 times (localhost is fast)
    const retryDelay = 2; // Wait 2 seconds between retries

    while (retryCount < maxRetries) {
      try {
        var request = http.MultipartRequest(
          'POST',
          Uri.parse('$serverUrl/detect'),
        );

        // Add image file
        request.files.add(
          await http.MultipartFile.fromPath('image', imageFile.path),
        );

        // Send request with timeout (local server is fast - shorter timeout)
        var streamedResponse = await request.send().timeout(
          const Duration(seconds: 30),
          onTimeout: () {
            throw Exception(
                'Request timeout - local server may not be running. Make sure Flask server is started on localhost:5000');
          },
        );

        var response = await http.Response.fromStream(streamedResponse);

        // Handle 502 Bad Gateway (server waking up / loading models) - retry automatically
        if (response.statusCode == 502) {
          retryCount++;
          if (retryCount < maxRetries) {
            print(
                '⚠️ Server returned 502 (models loading). Retrying in ${retryDelay}s... (Attempt $retryCount/$maxRetries)');
            await Future.delayed(Duration(seconds: retryDelay));
            continue; // Retry the request
          } else {
            throw Exception(
                'Server error (502) after $maxRetries attempts. Make sure Flask server is running on localhost:5000');
          }
        }

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
          throw Exception(responseData['error'] ??
              'Server error (status: ${response.statusCode})');
        }
      } catch (e) {
        // If it's not a 502 and we haven't retried yet, check if we should retry
        final errorStr = e.toString();
        if (!errorStr.contains('502') && retryCount == 0) {
          print('❌ Backend detection error: $e');
          rethrow;
        }
        // If we've exhausted retries, throw
        if (retryCount >= maxRetries - 1) {
          print('❌ Backend detection error after $maxRetries attempts: $e');
          rethrow;
        }
        // For 502 errors or timeout, continue to retry
        if (errorStr.contains('502') || errorStr.contains('timeout')) {
          retryCount++;
          if (retryCount < maxRetries) {
            print(
                '⏳ Waiting ${retryDelay}s before retry ($retryCount/$maxRetries)...');
            await Future.delayed(Duration(seconds: retryDelay));
          }
        } else {
          // Other errors - don't retry
          print('❌ Backend detection error: $e');
          rethrow;
        }
      }
    }

    throw Exception('Failed after $maxRetries attempts');
  }

  /// Detect fruits with tracking for live detection
  Future<Map<String, dynamic>> detectFruitsLive(File imageFile) async {
    int retryCount = 0;
    const maxRetries = 2; // Try up to 2 times (localhost is fast)
    const retryDelay = 2; // Wait 2 seconds between retries

    while (retryCount < maxRetries) {
      try {
        var request = http.MultipartRequest(
          'POST',
          Uri.parse('$serverUrl/detect_live'),
        );

        // Add image file
        request.files.add(
          await http.MultipartFile.fromPath('image', imageFile.path),
        );

        // Send request with timeout (local server is fast - shorter timeout)
        var streamedResponse = await request.send().timeout(
          const Duration(seconds: 30),
          onTimeout: () {
            throw Exception(
                'Request timeout - local server may not be running. Make sure Flask server is started on localhost:5000');
          },
        );

        var response = await http.Response.fromStream(streamedResponse);

        // Handle 502 Bad Gateway (server waking up / loading models) - retry automatically
        if (response.statusCode == 502) {
          retryCount++;
          if (retryCount < maxRetries) {
            print(
                '⚠️ Server returned 502 (models loading). Retrying in ${retryDelay}s... (Attempt $retryCount/$maxRetries)');
            await Future.delayed(Duration(seconds: retryDelay));
            continue; // Retry the request
          } else {
            throw Exception(
                'Server error (502) after $maxRetries attempts. Make sure Flask server is running on localhost:5000');
          }
        }

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
        // If it's not a 502 and we haven't retried yet, check if we should retry
        final errorStr = e.toString();
        if (!errorStr.contains('502') &&
            !errorStr.contains('timeout') &&
            retryCount == 0) {
          print('❌ Live detection error: $e');
          rethrow;
        }
        // If we've exhausted retries, throw
        if (retryCount >= maxRetries - 1) {
          print('❌ Live detection error after $maxRetries attempts: $e');
          rethrow;
        }
        // For 502 errors or timeout, continue to retry
        if (errorStr.contains('502') || errorStr.contains('timeout')) {
          retryCount++;
          if (retryCount < maxRetries) {
            print(
                '⏳ Waiting ${retryDelay}s before retry ($retryCount/$maxRetries)...');
            await Future.delayed(Duration(seconds: retryDelay));
          }
        } else {
          // Other errors - don't retry
          print('❌ Live detection error: $e');
          rethrow;
        }
      }
    }

    throw Exception('Failed after $maxRetries attempts');
  }

  /// Reset tracker for new counting session
  Future<bool> resetTracker() async {
    try {
      var response = await http
          .post(Uri.parse('$serverUrl/reset_tracker'))
          .timeout(const Duration(seconds: 10));

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
          print(
              '⏱️ Health check timeout - local server may not be running');
          throw Exception(
              'Connection timeout - make sure Flask server is running on localhost:5000');
        },
      );

      print('📊 Health check response: ${response.statusCode}');
      print('📄 Response body: ${response.body}');

      if (response.statusCode == 200) {
        print('✅ Server is healthy');
        return true;
      } else if (response.statusCode == 502) {
        print(
            '⚠️ Server returned 502 (Bad Gateway) - local server may not be running');
        print(
            '💡 Make sure Flask server is started: python3 lib/backend/backend_server_example.py');
        return false;
      } else {
        print('❌ Server returned status: ${response.statusCode}');
        print('💡 Response body: ${response.body}');
        return false;
      }
    } on SocketException catch (e) {
      print('❌ Network error: ${e.message}');
      print('💡 Make sure:');
      print('   1. Local Flask server is running: $serverUrl');
      print('   2. Server URL matches your laptop IP: $serverUrl');
      print('   3. Device is on the same network as your laptop');
      print('   4. Firewall allows connections on port 5000');
      return false;
    } on HttpException catch (e) {
      print('❌ HTTP error: ${e.message}');
      return false;
    } catch (e) {
      print('❌ Server health check failed: $e');
      print('💡 Server URL: $serverUrl');
      print('💡 Start local server: python3 lib/backend/backend_server_example.py');
      print('💡 Or use start script: ./lib/backend/start_server.sh');
      return false;
    }
  }
}
