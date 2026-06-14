import 'package:dio/dio.dart';

class ApiService {
  final Dio _dio = Dio();

  // 🔴 FastAPI সার্ভার লোকালহোল্টে চললে:
  // অ্যান্ড্রয়েড ইমুলেটরের জন্য: 'http://10.0.2.2:8000'
  // রিয়েল ডিভাইস বা আইফোনের জন্য পিসির IP (যেমন: http://192.168.x.x:8000)
  final String baseUrl = "http://192.168.1.2:8000";

  Future<String> sendMessage(String query,
      {String userId = "guest_user"}) async {
    try {
      final response = await _dio.post(
        '$baseUrl/chat',
        data: {
          "user_id": userId,
          "query": query,
          "model": "llama-3.1-8b-instant", // ডিফল্ট মডেল
        },
      );

      if (response.statusCode == 200) {
        return response.data['reply'] ?? "No response received.";
      }
      return "⚠️ Unexpected Error: ${response.statusCode}";
    } on DioException catch (e) {
      // ব্যাকএন্ডের 403 (Low Credit) বা 500 (Server Error) হ্যান্ডেল করা
      if (e.response != null) {
        return e.response?.data['reply'] ?? "⚠️ AI Engine Error!";
      }
      return "🔌 Connection failed. Is the FastAPI server running?";
    } catch (e) {
      return "⚠️ System Error: $e";
    }
  }
}
