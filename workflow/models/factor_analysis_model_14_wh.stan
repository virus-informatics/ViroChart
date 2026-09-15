data {
  int<lower=1> N;
  int<lower=1> D;
  int<lower=1> K;
  matrix[N, D] Y;

  // W prior 用ラプラシアン
  matrix[D, D] L_w;
  real<lower=0> lambda_w;
}

parameters {
  // 潜在因子
  matrix[N, K] z;                // 各サンプルの潜在因子

  // ローディング
  matrix[D, K] W_raw;            // ローディング（非負化前）

  // ノイズ（次元ごと）
  vector<lower=0>[D] psi;        // 観測ノイズ標準偏差 σ_d
}

transformed parameters {
  matrix[D, K] W;                // 非負ローディング
  matrix[N, D] eta;

  // 非負化（softplus）
  for (k in 1:K) {
    for (d in 1:D) {
      W[d, k] = log1p_exp(W_raw[d, k]);
    }
  }

  // 線形予測子（H_host なし）
  eta = z * W';
}

model {
  // 潜在因子
  to_vector(z) ~ normal(0, 1);

  // ローディングの弱情報事前
  to_vector(W_raw) ~ normal(0, 1);

  // Laplacian prior（パスウェイ間構造）
  for (k in 1:K) {
    target += -0.5 * lambda_w
              * quad_form(L_w, W_raw[, k]);
  }

  // 観測ノイズ
  psi ~ student_t(3, 0, 0.5);

  // 尤度
  for (d in 1:D) {
    Y[, d] ~ normal(eta[, d], psi[d]);
  }
}

generated quantities {
  matrix[N, D] y_rep;
  matrix[N, D] log_lik;
  vector[N] log_lik_sum;
  matrix[N, K] z_out;

  for (n in 1:N) {
    real tmp_sum = 0;
    for (d in 1:D) {
      y_rep[n, d] = normal_rng(eta[n, d], psi[d]);
      log_lik[n, d] = normal_lpdf(Y[n, d] | eta[n, d], psi[d]);
      tmp_sum += log_lik[n, d];
    }
    log_lik_sum[n] = tmp_sum;

    for (k in 1:K)
      z_out[n, k] = z[n, k];
  }
}
