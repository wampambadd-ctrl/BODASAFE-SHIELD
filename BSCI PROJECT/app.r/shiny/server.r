# server.R
library(shiny)
library(httr2)  # For forecast API
library(xgboost)
library("lubridate")

function(input, output) {
  gbm_model <- readRDS("C:/Users/THIRD YEAR/OneDrive/Desktop/Data analysis 3/BSCI PROJECT/gbm_model.rds")
  
  pred_premium <- reactive({
    # Fetch forecast precip (next day)
    req_forecast <- request("https://api.open-meteo.com/v1/forecast") %>%
      req_url_query(latitude = input$lat, longitude = input$lon, daily = "precipitation_sum")
    resp <- req_perform(req_forecast) %>% resp_body_json()
    precip <- resp$daily$precipitation_sum[[1]]  # Tomorrow's precip
    trigger <- ifelse(precip > 10, 1, 0)
    month_num <- month(Sys.Date() + days(1))
    
    # Predict via GBM (simplified)
    X_new <- matrix(c(month_num, trigger), nrow=1)
    pred_freq <- predict(gbm_model, X_new)
    premium <- pred_freq * input$hours * 3000  # Scale by hours, base UGX 3k/hr
    return(premium)
  })
  
  output$premium_text <- renderText({
    paste("Estimated Monthly Premium: UGX", round(pred_premium()))
  })
}
# Run: shiny::runApp()
