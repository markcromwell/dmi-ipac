package com.dmimfg.wcac

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/**
 * MainActivity — DMI WCAC Heat Exchanger calculator for Android.
 *
 * Jetpack Compose UI. All calculation happens server-side via WcacApi;
 * the proprietary engine is never shipped in the app.
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { WcacTheme { WcacScreen() } }
    }
}

@Composable
fun WcacTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = darkColorScheme(
            primary = Color(0xFF3B82F6),
            background = Color(0xFF111827),
            surface = Color(0xFF1F2937),
            onBackground = Color(0xFFF9FAFB),
            onSurface = Color(0xFFF9FAFB),
        ),
        content = content
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WcacScreen() {
    val scope = rememberCoroutineScope()
    var inputs by remember { mutableStateOf(WcacInputs()) }
    var result by remember { mutableStateOf<WcacResult?>(null) }
    var warnings by remember { mutableStateOf<List<Issue>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("DIVERSIFIED MANUFACTURING INC.",
                            fontWeight = FontWeight.Bold, fontSize = 15.sp)
                        Text("IPAC Heat Exchanger Calculator",
                            fontSize = 11.sp, color = Color(0xFF9CA3AF))
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = Color(0xFF111827))
            )
        }
    ) { pad ->
        Column(
            Modifier.padding(pad).padding(16.dp).verticalScroll(rememberScrollState())
        ) {
            // ── Inputs ──
            SectionLabel("AFTERCOOLER")
            TextField2("Model", inputs.model) { inputs = inputs.copy(model = it) }

            SectionLabel("TUBE SIDE (GAS)")
            TextField2("Fluid", inputs.tube_fluid) { inputs = inputs.copy(tube_fluid = it) }
            NumField("Inlet pressure (psig)", inputs.tube_pressure_psig) {
                inputs = inputs.copy(tube_pressure_psig = it) }
            NumField("Inlet temperature (F)", inputs.tube_temp_in_F) {
                inputs = inputs.copy(tube_temp_in_F = it) }
            NumField("Flow (Scfm)", inputs.tube_flow) { inputs = inputs.copy(tube_flow = it) }

            SectionLabel("SHELL SIDE (WATER)")
            NumField("Inlet temperature (F)", inputs.shell_temp_in_F) {
                inputs = inputs.copy(shell_temp_in_F = it) }
            NumField("Flow (USgpm)", inputs.shell_flow) { inputs = inputs.copy(shell_flow = it) }

            SectionLabel("COMPRESSOR SUCTION")
            NumField("Pressure (psia)", inputs.suction_pressure_psia) {
                inputs = inputs.copy(suction_pressure_psia = it) }
            NumField("Temperature (F)", inputs.suction_temp_F) {
                inputs = inputs.copy(suction_temp_F = it) }
            NumField("Relative humidity (%)", inputs.suction_rh_pct) {
                inputs = inputs.copy(suction_rh_pct = it) }

            Spacer(Modifier.height(16.dp))
            Button(
                onClick = {
                    loading = true; error = null
                    scope.launch {
                        try {
                            val resp = withContext(Dispatchers.IO) { WcacApi.calculate(inputs) }
                            result = resp.result; warnings = resp.warnings
                        } catch (e: Exception) {
                            error = e.message; result = null
                        } finally { loading = false }
                    }
                },
                enabled = !loading,
                modifier = Modifier.fillMaxWidth()
            ) { Text(if (loading) "Calculating…" else "CALCULATE PERFORMANCE") }

            error?.let {
                Spacer(Modifier.height(8.dp))
                Text(it, color = Color(0xFFF87171))
            }
            warnings.forEach {
                Text("⚠ ${it.message}", color = Color(0xFFFBBF24), fontSize = 12.sp)
            }

            // ── Results ──
            result?.let { r ->
                Spacer(Modifier.height(16.dp))
                SectionLabel("RESULTS")
                Card(colors = CardDefaults.cardColors(containerColor = Color(0xFF1F2937))) {
                    Column(Modifier.padding(16.dp)) {
                        ResultRow("Total heat", "%,.0f Btu/h".format(r.Q_Btu_h), hi = true)
                        ResultRow("Tube outlet", "%.1f F".format(r.tube_out_F))
                        ResultRow("Shell outlet", "%.1f F".format(r.shell_out_F))
                        ResultRow("Dew point", "%.1f F".format(r.dew_point_F))
                        ResultRow("Tube dP", "%.2f psi".format(r.dP_tube_psi))
                        ResultRow("Shell dP", "%.2f psi".format(r.dP_shell_psi))
                        ResultRow("Overall U", "%.0f Btu/h.ft2.R".format(r.overall_U_btu))
                        ResultRow("LMTD", "%.1f R".format(r.LMTD_R))
                        ResultRow("Surface area", "%.1f ft2".format(r.area_ft2))
                        ResultRow("Condensate", "%.1f lb/h".format(r.condensate_lb_h))
                    }
                }
            }
        }
    }
}

@Composable
fun SectionLabel(text: String) {
    Text(text, color = Color(0xFF6B7280), fontWeight = FontWeight.Bold,
        fontSize = 11.sp, modifier = Modifier.padding(top = 14.dp, bottom = 4.dp))
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TextField2(label: String, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value, onValueChange = onChange,
        label = { Text(label) }, singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NumField(label: String, value: Double, onChange: (Double) -> Unit) {
    var text by remember(value) { mutableStateOf(value.toString()) }
    OutlinedTextField(
        value = text,
        onValueChange = { text = it; it.toDoubleOrNull()?.let(onChange) },
        label = { Text(label) }, singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)
    )
}

@Composable
fun ResultRow(label: String, value: String, hi: Boolean = false) {
    Row(Modifier.fillMaxWidth().padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = Color(0xFF9CA3AF), fontSize = 13.sp)
        Text(value, fontFamily = FontFamily.Monospace, fontWeight = FontWeight.Bold,
            fontSize = 14.sp, color = if (hi) Color(0xFF34D399) else Color(0xFFF9FAFB))
    }
}
