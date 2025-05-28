import ModelClient, { isUnexpected } from "@azure-rest/ai-inference";
import { AzureKeyCredential } from "@azure/core-auth";

// Validate environment variable
const token = process.env["GITHUB_TOKEN"];
if (!token) {
  throw new Error("GITHUB_TOKEN environment variable is not set.");
}

const endpoint = "https://models.github.ai/inference"; // Verify this is the correct endpoint
const model = "xai/grok-3-mini";

async function main() {
  try {
    // Initialize the client
    const client = ModelClient(endpoint, new AzureKeyCredential(token));

    // Make the API request
    const response = await client.path("/chat/completions").post({
      body: {
        messages: [
          { role: "system", content: "You are a helpful assistant." },
          { role: "user", content: "What is the capital of France?" },
        ],
        temperature: 1.0,
        top_p: 1.0,
        model: model,
      },
    });

    // Check for unexpected response
    if (isUnexpected(response)) {
      const error = response.body?.error;
      throw new Error(
        `API request failed: ${error?.message || "Unknown error"} (Status: ${response.status})`
      );
    }

    // Validate response structure
    if (!response.body.choices || !response.body.choices[0]?.message?.content) {
      throw new Error("Unexpected response structure: Missing choices or content.");
    }

    // Output the response
    console.log(response.body.choices[0].message.content);
  } catch (err) {
    console.error("Error in main:", {
      message: err.message || "Unknown error",
      stack: err.stack,
    });
    throw err; // Re-throw to ensure the error is caught by the outer catch block
  }
}

main().catch((err) => {
  console.error("The sample encountered an error:", {
    message: err.message || "Unknown error",
    stack: err.stack,
  });
});
