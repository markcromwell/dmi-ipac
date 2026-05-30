package com.dmimfg.wcac

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import java.net.HttpURLConnection
import java.net.URL

/**
 * WcacApi — thin client for the WCAC REST API.
 *
 * The proprietary calculation engine runs server-side; this app only sends
 * inputs and renders results. Point BASE_URL at your deployed FastAPI service.
 */

@Serializable
data class WcacInputs(
    val model: String = "W0230",
    val bundle_type: String = "Fixed",
    val tube_type: String = "Std groove",
    val tube_material: String = "Stainless (S3040*)",
    val tube_fluid: String = "Air",
    val tube_pressure_psig: Double = 150.0,
    val tube_temp_in_F: Double = 250.0,
    val tube_flow: Double = 1423.0,
    val tube_flow_uom: String = "Scfm",
    val tube_fouling: Double = 0.0,
    val shell_fluid: String = "Water",
    val shell_temp_in_F: Double = 70.0,
    val shell_flow: Double = 60.0,
    val shell_flow_uom: String = "USgpm",
    val shell_fouling: Double = 0.0,
    val glycol_concentration: Double = 40.0,
    val suction_pressure_psia: Double = 14.7,
    val suction_temp_F: Double = 85.0,
    val suction_rh_pct: Double = 36.0,
    val surface_area_margin: Double = 0.0
)

@Serializable
data class WcacResult(
    val Q_Btu_h: Double = 0.0,
    val tube_out_F: Double = 0.0,
    val shell_out_F: Double = 0.0,
    val dew_point_F: Double = 0.0,
    val dP_tube_psi: Double = 0.0,
    val dP_shell_psi: Double = 0.0,
    val condensate_lb_h: Double = 0.0,
    val condensing_Btu_h: Double = 0.0,
    val condensing_pct: Double = 0.0,
    val overall_U_btu: Double = 0.0,
    val tube_HTC_btu: Double = 0.0,
    val shell_HTC_btu: Double = 0.0,
    val LMTD_R: Double = 0.0,
    val area_ft2: Double = 0.0,
    val tube_Re: Double = 0.0,
    val shell_Re: Double = 0.0,
    val Nt: Int = 0,
    val tube_wall_temps_F: List<Double> = emptyList()
)

@Serializable
data class Issue(val severity: String, val field: String, val message: String)

@Serializable
data class CalculateResponse(val result: WcacResult, val warnings: List<Issue> = emptyList())

object WcacApi {
    // TODO: set to your deployed API. For an emulator hitting a local server
    // use http://10.0.2.2:8000 ; for a device on the LAN use the host IP.
    var BASE_URL = "https://dmi-wcac-api.example.com"

    private val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

    /** POST /calculate — returns the result or throws with the server message. */
    fun calculate(inputs: WcacInputs): CalculateResponse {
        val body = json.encodeToString(WcacInputs.serializer(), inputs)
        val (code, text) = post("/calculate", body)
        if (code == 422) {
            throw WcacException("Invalid inputs: $text")
        }
        if (code !in 200..299) {
            throw WcacException("Server error $code: $text")
        }
        return json.decodeFromString(CalculateResponse.serializer(), text)
    }

    /** GET /models — list of valid model codes. */
    fun models(): List<String> {
        val (_, text) = get("/models")
        val obj = json.parseToJsonElement(text)
        // { "models": ["W0035", ...] }
        return json.decodeFromString(ModelsResponse.serializer(), text).models
    }

    @Serializable
    data class ModelsResponse(val models: List<String>)

    // ── HTTP helpers (plain HttpURLConnection — no extra dependency) ──────────

    private fun post(path: String, body: String): Pair<Int, String> {
        val conn = (URL(BASE_URL + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"
            doOutput = true
            connectTimeout = 15000
            readTimeout = 30000
            setRequestProperty("Content-Type", "application/json")
        }
        conn.outputStream.use { it.write(body.toByteArray()) }
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.bufferedReader()?.use { it.readText() } ?: ""
        return code to text
    }

    private fun get(path: String): Pair<Int, String> {
        val conn = (URL(BASE_URL + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "GET"
            connectTimeout = 15000
            readTimeout = 30000
        }
        val code = conn.responseCode
        val stream = if (code in 200..299) conn.inputStream else conn.errorStream
        val text = stream?.bufferedReader()?.use { it.readText() } ?: ""
        return code to text
    }
}

class WcacException(message: String) : Exception(message)
