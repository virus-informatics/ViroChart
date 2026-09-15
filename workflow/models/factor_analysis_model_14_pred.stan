data {
  int<lower=1> N;        // 新規サンプル数
  int<lower=1> D;        // 観測次元
  int<lower=1> K;        // 潜在因子数

  matrix[N, D] Y;        // 新規データ

  // 学習済みパラメータ
  matrix[D, K] W;        // 非負ローディング（固定）
  vector<lower=0>[D] psi_prior; // 観測ノイズ（固定）
}

parameters {
  matrix[N, K] z;        // 新規サンプルの潜在因子
}

transformed parameters {
  matrix[N, D] eta;
  eta = z * W';
}

model {
  // z の事前（学習時と同じ）
  to_vector(z) ~ normal(0, 1);

  // 尤度
  for (d in 1:D) {
    Y[, d] ~ normal(eta[, d], psi_prior[d]);
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
      y_rep[n, d] = normal_rng(eta[n, d], psi_prior[d]);
      log_lik[n, d] = normal_lpdf(Y[n, d] | eta[n, d], psi_prior[d]);
      tmp_sum += log_lik[n, d];
    }
    log_lik_sum[n] = tmp_sum;

    for (k in 1:K)
      z_out[n, k] = z[n, k];
  }
}
