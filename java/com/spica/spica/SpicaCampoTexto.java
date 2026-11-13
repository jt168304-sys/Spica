package com.spica.spica;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import android.text.InputType;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.inputmethod.EditorInfo;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.TextView;

// Campo de texto nativo do Android: usa o teclado do celular com correção e sugestões de verdade.
// Fica por cima do campo do Kivy, que fica invisível. Quando você envia, o texto volta para o Python.
public class SpicaCampoTexto {
    private static EditText campo;
    private static FrameLayout quadro;
    private static volatile String enviado = null;

    public static void mostrar(final Activity act, final int x, final int y, final int w, final int h, final String dica) {
        act.runOnUiThread(new Runnable() {
            public void run() {
                if (campo != null) {
                    posicionar(x, y, w, h);
                    return;
                }
                campo = new EditText(act);
                campo.setHint(dica);
                campo.setSingleLine(true);
                campo.setTextColor(Color.parseColor("#fef4ec"));
                campo.setHintTextColor(Color.parseColor("#a9aeb4"));
                campo.setTextSize(16);
                campo.setPadding(h / 2, 0, h / 2, 0);
                GradientDrawable fundo = new GradientDrawable();
                fundo.setCornerRadius(h / 2f);
                fundo.setColor(Color.parseColor("#1f2328"));
                fundo.setStroke(3, Color.parseColor("#a8c9bd"));
                campo.setBackground(fundo);
                campo.setInputType(InputType.TYPE_CLASS_TEXT
                        | InputType.TYPE_TEXT_FLAG_AUTO_CORRECT
                        | InputType.TYPE_TEXT_FLAG_CAP_SENTENCES);
                campo.setImeOptions(EditorInfo.IME_ACTION_SEND);
                campo.setOnEditorActionListener(new TextView.OnEditorActionListener() {
                    public boolean onEditorAction(TextView v, int acao, KeyEvent e) {
                        boolean enter = e != null && e.getKeyCode() == KeyEvent.KEYCODE_ENTER
                                && e.getAction() == KeyEvent.ACTION_DOWN;
                        if (acao == EditorInfo.IME_ACTION_SEND || acao == EditorInfo.IME_ACTION_DONE || enter) {
                            String t = v.getText().toString().trim();
                            if (!t.isEmpty()) {
                                enviado = t;
                                v.setText("");
                            }
                            return true;
                        }
                        return false;
                    }
                });
                quadro = new FrameLayout(act);
                quadro.addView(campo, new FrameLayout.LayoutParams(
                        FrameLayout.LayoutParams.MATCH_PARENT, FrameLayout.LayoutParams.MATCH_PARENT));
                FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(w, h, Gravity.TOP | Gravity.LEFT);
                lp.leftMargin = x;
                lp.topMargin = y;
                act.addContentView(quadro, lp);
            }
        });
    }

    private static void posicionar(final int x, final int y, final int w, final int h) {
        if (quadro == null) return;
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(w, h, Gravity.TOP | Gravity.LEFT);
        lp.leftMargin = x;
        lp.topMargin = y;
        quadro.setLayoutParams(lp);
    }

    public static void atualizar(final Activity act, final int x, final int y, final int w, final int h) {
        act.runOnUiThread(new Runnable() {
            public void run() { posicionar(x, y, w, h); }
        });
    }

    public static String pegarEnviado() {
        String t = enviado;
        enviado = null;
        return t;
    }

    public static String pegarTexto() {
        return campo == null ? "" : campo.getText().toString();
    }

    public static void limpar(final Activity act) {
        act.runOnUiThread(new Runnable() {
            public void run() { if (campo != null) campo.setText(""); }
        });
    }
}
