{
    "$schema": "https://opencode.ai/config.json",
    "provider": {
        "csi-provider": {
            "name": "csi.ai",
            "npm": "@ai-sdk/openai-compatible",
            "options": {
                "apiKey": "sk-FP1owtdEKvWUvw1dNSDTCA",
                "baseURL": "http://113.46.219.251:8080/v1",
                "setCacheKey": true
            },
            "models": {
                "DeepSeek-V4.1-Flash": {
                    "name": "DeepSeek-V4.1-Flash"
                },
                "GLM-5.2": {
                    "name": "GLM-5.2"
                },
				"GLM-5.3": {
                    "name": "GLM-5.3"
                },
				"GLM-5.3-Flash": {
					"name": "GLM-5.3-Flash"
				},
				"Qwen3.7-Plus": {
					"name": "Qwen3.7-Plus"
				},
				"Qwen3.8-Max": {
					"name": "Qwen3.8-Max"
				}
            }
        }
    }
}
